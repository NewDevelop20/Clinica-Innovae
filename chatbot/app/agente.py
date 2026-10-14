"""El "cerebro" común a todos los canales.

responder(sesion_id, texto, contexto) -> texto de respuesta

Bucle de herramientas:
  1. Se envía el historial a Claude con las instrucciones y las herramientas.
  2. Si Claude pide una herramienta (stop_reason == "tool_use"), se ejecuta y se le
     devuelve el resultado; se repite hasta que conteste con texto.
  3. Se guarda el historial de la conversación.
"""
from __future__ import annotations

import json
import logging
import re
from types import SimpleNamespace
from typing import Any, Callable

from .config import Config
from .conocimiento import tratamiento_oficial, tratamientos
from .herramientas import Contexto, Herramientas, definiciones
from .prompt import bloques_sistema
from .sesiones import AlmacenSesiones

log = logging.getLogger("innovae.agente")

MENSAJE_ERROR = (
    "Disculpe, ahora mismo no puedo responder. Puede escribirnos por WhatsApp o llamar "
    "al 661 73 48 70 y le atendemos enseguida."
)

LLM = Callable[..., Any]  # firma de client.messages.create


def _bloque_a_dict(b: Any) -> dict:
    """Convierte un bloque de la respuesta en un dict mínimo para guardarlo."""
    tipo = getattr(b, "type", None)
    if tipo == "text":
        return {"type": "text", "text": b.text}
    if tipo == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input or {})}
    # otros bloques (p. ej. thinking) se guardan tal cual si el SDK lo permite
    return b.model_dump(exclude_none=True) if hasattr(b, "model_dump") else dict(b)


class Agente:
    def __init__(self, config: Config, llm: LLM, herramientas: Herramientas,
                 sesiones: AlmacenSesiones):
        self.config = config
        self.llm = llm
        self.herramientas = herramientas
        self.sesiones = sesiones
        self._tools = definiciones()

    def responder(self, sesion_id: str, texto: str, ctx: Contexto | None = None) -> str:
        ctx = ctx or Contexto()
        with self.sesiones.lock_de(sesion_id):
            historial = self.sesiones.obtener(sesion_id)
            nuevo = historial + [{"role": "user", "content": texto}]
            try:
                respuesta, nuevo = self._bucle(nuevo, ctx)
            except Exception:  # noqa: BLE001 - nunca dejar al cliente sin respuesta
                log.exception("Fallo generando respuesta (sesión %s)", sesion_id)
                return MENSAJE_ERROR  # no se guarda un historial a medias
            self.sesiones.guardar(sesion_id, nuevo)
            return respuesta

    def _bucle(self, mensajes: list[dict], ctx: Contexto) -> tuple[str, list[dict]]:
        sistema = bloques_sistema(ctx.canal)
        for vuelta in range(self.config.max_iteraciones_herramientas + 1):
            resp = self.llm(
                model=self.config.modelo,
                max_tokens=self.config.max_tokens,
                system=sistema,
                tools=self._tools,
                messages=mensajes,
            )
            uso = getattr(resp, "usage", None)
            if uso is not None:
                log.info("tokens in=%s out=%s cache_read=%s", getattr(uso, "input_tokens", "?"),
                         getattr(uso, "output_tokens", "?"),
                         getattr(uso, "cache_read_input_tokens", "?"))

            bloques = [_bloque_a_dict(b) for b in resp.content]
            pide_herramientas = resp.stop_reason == "tool_use"
            ultima = vuelta == self.config.max_iteraciones_herramientas

            if pide_herramientas and ultima:
                # Demasiadas vueltas: no dejamos un tool_use sin respuesta en el historial.
                log.warning("Límite de herramientas alcanzado")
                mensajes.append({"role": "assistant", "content": [{"type": "text", "text": MENSAJE_ERROR}]})
                return MENSAJE_ERROR, mensajes

            mensajes.append({"role": "assistant", "content": bloques})
            if not pide_herramientas:
                texto = "\n\n".join(b["text"] for b in bloques if b.get("type") == "text").strip()
                return (texto or MENSAJE_ERROR), mensajes

            resultados = []
            for b in bloques:
                if b.get("type") != "tool_use":
                    continue
                res = self.herramientas.ejecutar(b["name"], b["input"], ctx)
                log.info("herramienta %s -> ok=%s", b["name"], res.get("ok"))
                resultados.append({
                    "type": "tool_result",
                    "tool_use_id": b["id"],
                    "content": json.dumps(res, ensure_ascii=False),
                    "is_error": not res.get("ok", True),
                })
            mensajes.append({"role": "user", "content": resultados})
        return MENSAJE_ERROR, mensajes  # inalcanzable


# --------------------------------------------------------------------------
#  Clientes de LLM
# --------------------------------------------------------------------------
def crear_llm(config: Config) -> LLM | None:
    if config.modo_simulado:
        return ClienteSimulado()
    if not config.anthropic_api_key:
        return None
    import anthropic

    cliente = anthropic.Anthropic(api_key=config.anthropic_api_key, max_retries=2, timeout=45.0)
    return cliente.messages.create


class ClienteSimulado:
    """Imita a Claude SIN API key, para probar web, WhatsApp y Code.gs de punta a punta.

    - Si el mensaje incluye un tratamiento y una fecha AAAA-MM-DD, consulta la
      disponibilidad REAL con la herramienta y devuelve las horas libres.
    - Si no, contesta con un texto fijo que repite lo recibido.
    """

    def __call__(self, *, messages: list[dict], **_: Any) -> SimpleNamespace:
        ultimo = messages[-1]
        contenido = ultimo["content"]

        # Vuelta 2: llega el resultado de la herramienta -> se resume.
        if isinstance(contenido, list) and contenido and contenido[0].get("type") == "tool_result":
            datos = json.loads(contenido[0]["content"])
            if datos.get("ok"):
                horas = ", ".join(datos["horas_libres"][:6]) or "ninguna"
                txt = f"[SIMULADO] {datos['tratamiento']} el {datos['dia']}: horas libres {horas}."
            else:
                txt = f"[SIMULADO] No he podido consultar la agenda: {datos.get('error')}"
            return _respuesta_texto(txt)

        texto = contenido if isinstance(contenido, str) else ""
        fecha = re.search(r"\d{4}-\d{2}-\d{2}", texto)
        trat = next((t for t in tratamientos() if tratamiento_oficial(t)
                     and t.lower() in texto.lower()), None)
        if fecha and trat:
            bloque = SimpleNamespace(type="tool_use", id="sim_1", name="consultar_disponibilidad",
                                     input={"fecha": fecha.group(0), "tratamiento": trat})
            return SimpleNamespace(content=[bloque], stop_reason="tool_use", usage=None)

        return _respuesta_texto(
            "[SIMULADO] Hola, soy el asistente de Clínica Innovae en modo de prueba (sin IA). "
            f"He recibido: «{texto[:200]}». Para probar la agenda escriba, por ejemplo: "
            "«Limpieza Facial 2026-10-20»."
        )


def _respuesta_texto(txt: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=txt)],
                           stop_reason="end_turn", usage=None)

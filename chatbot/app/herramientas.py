"""Herramientas que Claude puede usar. Hablan con el Code.gs ya existente:

  GET  {APPS_SCRIPT_URL}?disponibilidad=YYYY-MM-DD&tratamiento=X
       -> {"ok": true, "bloqueadas": ["10:00", ...]}
  POST {APPS_SCRIPT_URL}  (JSON con los mismos campos que el formulario web)
       -> {"ok": true, "id": "AB12CD34"} | {"ok": false, "error": "...", "motivo": "..."}

Así la reserva del chatbot entra EXACTAMENTE igual que la del formulario:
evento 🟡 PENDIENTE en el calendario y email Confirmar/Rechazar, sin hoja de cálculo.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from . import horario
from .conocimiento import tratamiento_oficial, tratamientos

log = logging.getLogger("innovae.herramientas")

CONTACTO = {
    "telefono": "661 73 48 70",
    "whatsapp": "https://wa.me/34661734870",
    "reservas_web": "https://newdevelop20.github.io/Clinica-Innovae/#reservas",
}


# --------------------------------------------------------------------------
#  Cliente del Web App de Apps Script
# --------------------------------------------------------------------------
class ErrorReservas(Exception):
    pass


class AppsScriptCliente:
    def __init__(self, url: str, timeout: float = 20.0, transport: httpx.BaseTransport | None = None):
        self.url = url
        # Apps Script responde con una redirección 302 a googleusercontent.com:
        # hay que seguirla para leer el JSON.
        self._http = httpx.Client(timeout=timeout, follow_redirects=True, transport=transport)

    @property
    def configurado(self) -> bool:
        return bool(self.url)

    def _json(self, r: httpx.Response) -> dict:
        r.raise_for_status()
        try:
            return r.json()
        except ValueError as e:
            raise ErrorReservas("Respuesta no válida del sistema de reservas") from e

    def horas_bloqueadas(self, fecha: str, tratamiento: str, profesional: str = "") -> list[str]:
        params = {"disponibilidad": fecha, "tratamiento": tratamiento}
        if profesional:
            params["profesional"] = profesional
        r = self._http.get(self.url, params=params)
        datos = self._json(r)
        if not datos.get("ok"):
            raise ErrorReservas(datos.get("error") or "Error consultando disponibilidad")
        return list(datos.get("bloqueadas") or [])

    def profesionales(self) -> list[dict]:
        datos = self._json(self._http.get(self.url, params={"catalogo": "profesionales"}))
        if not datos.get("ok") or not isinstance(datos.get("profesionales"), list):
            raise ErrorReservas("No se pudo consultar el equipo disponible")
        return datos["profesionales"]

    def crear_reserva(self, campos: dict[str, Any]) -> dict:
        # Se envía como texto plano con JSON dentro: leerDatos_() de Code.gs lo detecta
        # (empieza por "{"), y así se evita cualquier problema de content-type.
        r =self._http.post(self.url, content=json.dumps(campos, ensure_ascii=False),
                            headers={"Content-Type": "text/plain;charset=utf-8"})
        return self._json(r)


# --------------------------------------------------------------------------
#  Definición de herramientas (lo que ve Claude)
# --------------------------------------------------------------------------
def definiciones() -> list[dict]:
    lista = ", ".join(tratamientos())
    return [
        {
            "name": "consultar_profesionales",
            "description": "Consulta los IDs, nombres y tratamientos de los profesionales. Úsala antes de proponer un profesional; nunca inventes nombres ni atribuciones. Si no hay preferencia, usa cualquiera.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "consultar_disponibilidad",
            "description": (
                "Devuelve las horas LIBRES para un tratamiento en una fecha concreta, según la agenda real "
                "de la clínica. Úsala siempre antes de proponer horas; nunca inventes disponibilidad. "
                "Si el día está cerrado o completo, prueba con otra fecha cercana."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "fecha": {"type": "string", "description": "Fecha en formato AAAA-MM-DD."},
                    "profesional": {"type": "string", "description": "ID devuelto por consultar_profesionales, o cualquiera si no hay preferencia."},
                    "tratamiento": {"type": "string", "description": f"Nombre exacto de uno de: {lista}."},
                },
                "required": ["fecha", "tratamiento"],
            },
        },
        {
            "name": "crear_solicitud_reserva",
            "description": (
                "Crea una SOLICITUD de cita (queda pendiente de que la clínica la confirme). "
                "Úsala SOLO después de haber mostrado al cliente el resumen completo (tratamiento, fecha, hora, "
                "nombre y teléfono) y de que haya respondido afirmativamente."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "tratamiento": {"type": "string", "description": "Nombre exacto del tratamiento."},
                    "fecha": {"type": "string", "description": "AAAA-MM-DD"},
                    "hora": {"type": "string", "description": "HH:MM, una de las horas libres consultadas."},
                    "profesional": {"type": "string", "description": "El mismo ID usado al consultar disponibilidad, o cualquiera."},
                    "nombre": {"type": "string", "description": "Nombre y apellidos del cliente."},
                    "telefono": {"type": "string", "description": "Teléfono de contacto (9+ dígitos)."},
                    "email": {"type": "string", "description": "Opcional. Para recibir la confirmación."},
                    "primera_visita": {"type": "boolean", "description": "¿Es su primera vez en la clínica?"},
                    "comentarios": {"type": "string", "description": "Opcional. Notas breves del cliente."},
                    "cliente_ha_confirmado": {
                        "type": "boolean",
                        "description": "true solo si el cliente ha confirmado explícitamente el resumen.",
                    },
                },
                "required": ["tratamiento", "fecha", "hora", "nombre", "telefono", "cliente_ha_confirmado"],
            },
        },
        {
            "name": "derivar_a_persona",
            "description": (
                "Úsala cuando el cliente pida hablar con una persona, cuando la consulta sea médica o personal "
                "(salud, embarazo, medicación, reacciones), una queja, un cambio o cancelación de cita, o "
                "cuando no tengas la información. Devuelve cómo contactar con la clínica."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"motivo": {"type": "string", "description": "Motivo breve."}},
                "required": ["motivo"],
            },
        },
    ]


# --------------------------------------------------------------------------
#  Ejecución
# --------------------------------------------------------------------------
@dataclass
class Contexto:
    canal: str = "web"              # "web" | "whatsapp"
    telefono: str | None = None     # en WhatsApp lo conocemos por el número


class Herramientas:
    def __init__(self, cliente: AppsScriptCliente):
        self.cliente = cliente

    def ejecutar(self, nombre: str, datos: dict, ctx: Contexto) -> dict:
        try:
            if nombre == "consultar_profesionales":
                if not self.cliente.configurado:
                    return {"ok": False, "error": "La agenda no está conectada.", "alternativa": CONTACTO}
                return {"ok": True, "profesionales": self.cliente.profesionales()}
            if nombre == "consultar_disponibilidad":
                return self.consultar_disponibilidad(**_solo(datos, "fecha", "tratamiento", "profesional"))
            if nombre == "crear_solicitud_reserva":
                return self.crear_solicitud_reserva(datos, ctx)
            if nombre == "derivar_a_persona":
                log.info("Derivación a persona (%s): %s", ctx.canal, datos.get("motivo"))
                return {"ok": True, "contacto": CONTACTO,
                        "indicacion": "Da al cliente el teléfono/WhatsApp de la clínica."}
            return {"ok": False, "error": f"Herramienta desconocida: {nombre}"}
        except ErrorReservas as e:
            log.warning("Error de reservas: %s", e)
            return {"ok": False, "error": str(e), "alternativa": CONTACTO}
        except httpx.HTTPError as e:
            log.exception("Fallo de red con Apps Script")
            return {"ok": False, "error": "El sistema de reservas no responde ahora mismo.",
                    "alternativa": CONTACTO}

    # -- disponibilidad ---------------------------------------------------
    def consultar_disponibilidad(self, fecha: str = "", tratamiento: str = "", profesional: str = "") -> dict:
        oficial = tratamiento_oficial(tratamiento)
        if not oficial:
            return {"ok": False, "error": f"Tratamiento no reconocido: '{tratamiento}'.",
                    "tratamientos_validos": list(tratamientos())}
        d = horario.parsear_fecha(fecha)
        if not d:
            return {"ok": False, "error": "Fecha no válida; usa AAAA-MM-DD."}
        motivo = horario.motivo_fecha_no_valida(d)
        if motivo:
            return {"ok": False, "fecha": fecha, "error": motivo}
        posibles = horario.horas_posibles(d)
        if not self.cliente.configurado:
            return {"ok": False, "error": "La reserva online no está activa todavía.",
                    "alternativa": CONTACTO}
        bloqueadas = set(self.cliente.horas_bloqueadas(d.isoformat(), oficial, profesional))
        libres = [h for h in posibles if h not in bloqueadas]
        return {"ok": True, "fecha": d.isoformat(), "dia": horario.fecha_legible(d),
                "tratamiento": oficial, "profesional": profesional or "cualquiera", "horas_libres": libres,
                "nota": "Sin horas libres ese día." if not libres else None}

    # -- reserva ---------------------------------------------------------------
    def crear_solicitud_reserva(self, datos: dict, ctx: Contexto) -> dict:
        if datos.get("cliente_ha_confirmado") is not True:
            return {"ok": False, "error": "Antes muestra el resumen al cliente y espera su confirmación."}

        nombre = re.sub(r"\s+", " ", str(datos.get("nombre") or "")).strip()[:100]
        telefono = re.sub(r"[^\d+]", "", str(datos.get("telefono") or ctx.telefono or ""))
        email = str(datos.get("email") or "").strip()
        hora = str(datos.get("hora") or "").strip()

        errores = []
        if len(nombre) < 2:
            errores.append("falta el nombre")
        if len(re.sub(r"\D", "", telefono)) < 9:
            errores.append("el teléfono debe tener al menos 9 dígitos")
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            errores.append("el email no parece válido")
        if errores:
            return {"ok": False, "error": "Datos incompletos: " + "; ".join(errores) + "."}

        # Se vuelve a comprobar la hora justo antes de reservar (otra persona pudo cogerla).
        disp = self.consultar_disponibilidad(datos.get("fecha", ""), datos.get("tratamiento", ""), datos.get("profesional", ""))
        if not disp.get("ok"):
            return disp
        if hora not in disp["horas_libres"]:
            return {"ok": False, "error": f"Las {hora} ya no están libres.",
                    "horas_libres": disp["horas_libres"]}

        origen = "Chatbot WhatsApp" if ctx.canal == "whatsapp" else "Chatbot web"
        comentarios = str(datos.get("comentarios") or "").strip()[:900]
        campos = {
            "nombre": nombre,
            "telefono": telefono,
            "email": email,
            "tratamiento": disp["tratamiento"],
            "fecha": disp["fecha"],
            "hora": hora,
            "primeraVisita": "true" if datos.get("primera_visita") else "false",
            "comentarios": f"[{origen}] {comentarios}".strip(),
            "website": "",  # honeypot vacío
        }
        if datos.get("profesional"):
            campos["profesional"] = datos["profesional"]
        res = self.cliente.crear_reserva(campos)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error") or "No se pudo registrar la solicitud.",
                    "motivo": res.get("motivo")}
        return {"ok": True, "id": res.get("id"), "estado": "PENDIENTE de confirmar por la clínica",
                "resumen": {k: campos[k] for k in ("tratamiento", "fecha", "hora", "nombre")},
                "dia": disp["dia"], "profesional": res.get("profesional"), "recibira_email": bool(email)}


def _solo(datos: dict, *claves: str) -> dict:
    return {k: datos.get(k, "") for k in claves}

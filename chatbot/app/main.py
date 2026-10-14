"""API del chatbot de Clínica Innovae.

Rutas:
  GET  /health                  -> estado y qué está configurado
  POST /api/chat                -> canal web (lo usa el widget)
  GET  /webhook/whatsapp        -> verificación de Meta
  POST /webhook/whatsapp        -> mensajes de WhatsApp
  GET  /widget/innovae-chat.js  -> el widget para pegar en la web
  GET  /demo                    -> página de prueba local con el widget

Arranque local:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import json
import logging
import re

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agente import Agente, crear_llm
from .config import RAIZ, Config
from .herramientas import AppsScriptCliente, Contexto, Herramientas
from .sesiones import AlmacenSesiones, Deduplicador, LimitadorMensajes
from .whatsapp import ClienteWhatsApp, extraer_mensajes, firma_valida

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("innovae")

SESION_VALIDA = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
AVISO_LIMITE = ("Ha enviado muchos mensajes seguidos. Espere unos minutos o escríbanos por "
                "WhatsApp al 661 73 48 70.")
AVISO_NO_TEXTO = ("De momento solo puedo leer mensajes de texto. ¿Me lo puede escribir? "
                  "Si prefiere hablar con el equipo, llame al 661 73 48 70.")


class PeticionChat(BaseModel):
    sesion_id: str = Field(..., description="ID aleatorio que genera el widget")
    mensaje: str


def crear_app(config: Config | None = None, *, llm=None,
              transporte_apps_script: httpx.BaseTransport | None = None,
              transporte_whatsapp: httpx.BaseTransport | None = None) -> FastAPI:
    config = config or Config.desde_entorno()
    llm = llm if llm is not None else crear_llm(config)

    sesiones = AlmacenSesiones(config.max_turnos_historial, config.caducidad_sesion_segundos)
    herramientas = Herramientas(AppsScriptCliente(config.apps_script_url, config.timeout_http,
                                                  transporte_apps_script))
    agente = Agente(config, llm, herramientas, sesiones) if llm else None
    limitador = LimitadorMensajes(config.max_mensajes_por_ventana, config.ventana_segundos)
    dedup = Deduplicador()
    wa = (ClienteWhatsApp(config.whatsapp_token, config.whatsapp_phone_number_id,
                          config.graph_api_version, transporte_whatsapp)
          if config.whatsapp_configurado else None)

    app = FastAPI(title="Chatbot Clínica Innovae", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=config.origenes_permitidos,
                       allow_methods=["POST", "GET", "OPTIONS"], allow_headers=["Content-Type"])

    # ---------------------------------------------------------------- estado
    @app.get("/health")
    def health():
        return {
            "ok": True,
            "ia": "simulada" if config.modo_simulado else ("activa" if agente else "sin API key"),
            "modelo": config.modelo,
            "reservas": "conectadas" if config.apps_script_url else "sin APPS_SCRIPT_URL",
            "whatsapp": "configurado" if wa else "sin credenciales",
        }

    # ------------------------------------------------------------- canal web
    @app.post("/api/chat")
    def chat(p: PeticionChat, request: Request):
        origen = request.headers.get("origin")
        if origen and origen not in config.origenes_permitidos:
            raise HTTPException(403, "Origen no permitido")
        if not SESION_VALIDA.fullmatch(p.sesion_id):
            raise HTTPException(400, "sesion_id no válido")
        texto = p.mensaje.strip()
        if not texto:
            raise HTTPException(400, "Mensaje vacío")
        if len(texto) > config.max_longitud_mensaje:
            return {"respuesta": f"El mensaje es demasiado largo (máx. {config.max_longitud_mensaje} "
                                 "caracteres). ¿Puede resumirlo?"}
        if not agente:
            raise HTTPException(503, "El asistente no está configurado (falta ANTHROPIC_API_KEY).")
        direccion = request.client.host if request.client else "desconocida"
        if not limitador.permitir(f"ip:{direccion}") or not limitador.permitir(f"web:{p.sesion_id}"):
            return JSONResponse({"respuesta": AVISO_LIMITE}, status_code=429)
        respuesta = agente.responder(f"web:{p.sesion_id}", texto, Contexto(canal="web"))
        return {"respuesta": respuesta}

    # -------------------------------------------------------- canal WhatsApp
    @app.get("/webhook/whatsapp")
    def verificar_webhook(modo: str = Query("", alias="hub.mode"),
                          token: str = Query("", alias="hub.verify_token"),
                          reto: str = Query("", alias="hub.challenge")):
        if modo == "subscribe" and config.whatsapp_verify_token and token == config.whatsapp_verify_token:
            return PlainTextResponse(reto)
        raise HTTPException(403, "Token de verificación incorrecto")

    @app.post("/webhook/whatsapp")
    async def recibir_whatsapp(request: Request):
        if not wa or not agente:
            raise HTTPException(503, "WhatsApp no está configurado")
        cuerpo = await request.body()
        if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256"),
                            config.whatsapp_app_secret):
            raise HTTPException(403, "Firma no válida")
        try:
            payload = json.loads(cuerpo or b"{}")
        except ValueError:
            raise HTTPException(400, "JSON no válido")
        if not isinstance(payload, dict):
            raise HTTPException(400, "JSON no válido")

        # Se procesa antes de responder: en Cloud Run el trabajo en segundo plano tras
        # la respuesta puede quedarse sin CPU. Si Meta reintenta, el deduplicador lo ignora.
        from starlette.concurrency import run_in_threadpool

        for m in extraer_mensajes(payload, config.whatsapp_phone_number_id):
            if not m.id or dedup.ya_visto(m.id):
                continue
            await run_in_threadpool(_atender_whatsapp, m)
        return {"ok": True}  # siempre 200 para que Meta no reintente en bucle

    def _atender_whatsapp(m) -> None:
        if not wa:
            log.warning("Mensaje de WhatsApp recibido pero faltan credenciales")
            return
        try:
            if not m.texto:
                wa.enviar_texto(m.de, AVISO_NO_TEXTO)
            elif not limitador.permitir(f"wa:{m.de}"):
                wa.enviar_texto(m.de, AVISO_LIMITE)
            elif not agente:
                log.error("WhatsApp sin IA configurada")
            else:
                texto = m.texto.strip()[: config.max_longitud_mensaje]
                respuesta = agente.responder(f"wa:{m.de}", texto,
                                             Contexto(canal="whatsapp", telefono=m.de))
                wa.enviar_texto(m.de, respuesta)
        except Exception:  # noqa: BLE001
            log.exception("Error atendiendo WhatsApp de %s", m.de[-4:])

    # ------------------------------------------------------------ widget/demo
    carpeta_widget = RAIZ / "widget"
    app.mount("/widget", StaticFiles(directory=carpeta_widget), name="widget")

    @app.get("/demo", include_in_schema=False)
    def demo():
        return FileResponse(carpeta_widget / "demo.html")

    app.state.agente = agente
    app.state.sesiones = sesiones
    return app


app = crear_app()

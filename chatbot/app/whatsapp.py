"""Canal WhatsApp (Cloud API de Meta).

- GET  /webhook/whatsapp : verificación inicial que hace Meta (hub.challenge).
- POST /webhook/whatsapp : Meta nos avisa de cada mensaje entrante.

Respondemos con un mensaje de texto normal. Eso está permitido dentro de la
"ventana de 24 h" que se abre cuando el cliente nos escribe; fuera de ella
(p. ej. recordatorios) harían falta plantillas aprobadas por Meta.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
from dataclasses import dataclass

import httpx

log = logging.getLogger("innovae.whatsapp")
LIMITE_TEXTO = 4000  # WhatsApp admite 4096 caracteres por mensaje


@dataclass
class MensajeEntrante:
    id: str
    de: str          # número del cliente (wa_id), p. ej. "34600111222"
    texto: str | None
    tipo: str


def firma_valida(cuerpo: bytes, cabecera: str | None, app_secret: str) -> bool:
    """Comprueba X-Hub-Signature-256 = sha256=HMAC(app_secret, cuerpo)."""
    if not app_secret:
        return False
    if not cabecera or not cabecera.startswith("sha256="):
        return False
    esperado = hmac.new(app_secret.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, cabecera.split("=", 1)[1])


def extraer_mensajes(payload: dict, phone_number_id: str = "") -> list[MensajeEntrante]:
    """Saca los mensajes de un webhook; ignora avisos de estado (entregado, leído…)."""
    salida: list[MensajeEntrante] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            valor = change.get("value") or {}
            if phone_number_id and (valor.get("metadata") or {}).get("phone_number_id") != phone_number_id:
                continue
            for m in valor.get("messages") or []:
                tipo = m.get("type", "")
                texto = None
                if tipo == "text":
                    texto = (m.get("text") or {}).get("body")
                elif tipo == "button":
                    texto = (m.get("button") or {}).get("text")
                elif tipo == "interactive":
                    i = m.get("interactive") or {}
                    texto = ((i.get("button_reply") or i.get("list_reply") or {}).get("title"))
                salida.append(MensajeEntrante(id=m.get("id", ""), de=m.get("from", ""),
                                              texto=texto, tipo=tipo))
    return salida


def adaptar_formato(texto: str) -> str:
    """Pasa el markdown típico al formato de WhatsApp por si el modelo se despista."""
    t = re.sub(r"\*\*(.+?)\*\*", r"*\1*", texto)            # **negrita** -> *negrita*
    t = re.sub(r"^#{1,6}\s*", "", t, flags=re.MULTILINE)     # sin encabezados
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1: \2", t)  # [texto](url) -> texto: url
    return t.strip()


def trocear(texto: str, limite: int = LIMITE_TEXTO) -> list[str]:
    if len(texto) <= limite:
        return [texto]
    partes, actual = [], ""
    for parrafo in texto.split("\n\n"):
        if len(actual) + len(parrafo) + 2 > limite and actual:
            partes.append(actual.strip())
            actual = ""
        actual += parrafo + "\n\n"
    if actual.strip():
        partes.append(actual.strip())
    return [p[i:i + limite] for p in partes for i in range(0, len(p), limite)]


class ClienteWhatsApp:
    def __init__(self, token: str, phone_number_id: str, version: str = "v21.0",
                 transport: httpx.BaseTransport | None = None):
        self.url = f"https://graph.facebook.com/{version}/{phone_number_id}/messages"
        self._http = httpx.Client(timeout=15.0, transport=transport,
                                  headers={"Authorization": f"Bearer {token}"})

    def enviar_texto(self, para: str, texto: str) -> None:
        for trozo in trocear(adaptar_formato(texto)):
            r = self._http.post(self.url, json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": para,
                "type": "text",
                "text": {"preview_url": False, "body": trozo},
            })
            if r.status_code >= 400:
                log.error("WhatsApp respondió %s: %s", r.status_code, r.text[:500])
                r.raise_for_status()

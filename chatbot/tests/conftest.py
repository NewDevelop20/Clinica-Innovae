"""Piezas falsas para probar TODO sin API key, sin Apps Script y sin Meta."""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta
from types import SimpleNamespace

import httpx
import pytest

from app import horario
from app.config import Config

APPS_URL = "https://script.google.com/macros/s/TEST/exec"
APP_SECRET = "secreto-de-prueba"


def proximo_dia(weekday: int) -> str:
    """Fecha ISO del próximo lunes(0)…sábado(5), siempre en el futuro (≥ 2 días)."""
    d = horario.ahora().date() + timedelta(days=2)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.isoformat()


# ------------------------------------------------------------ Apps Script falso
class AppsScriptFalso:
    """Imita el Code.gs: GET disponibilidad y POST reserva, con la redirección 302 real."""

    def __init__(self, bloqueadas=None, respuesta_post=None, fallo_red=False):
        self.bloqueadas = bloqueadas or []
        self.respuesta_post = respuesta_post or {"ok": True, "id": "AB12CD34"}
        self.fallo_red = fallo_red
        self.posts: list[dict] = []
        self.gets: list[dict] = []
        self._pendiente = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if self.fallo_red:
            raise httpx.ConnectError("sin red", request=request)
        if request.url.host == "script.google.com":
            if request.method == "POST":
                self.posts.append(json.loads(request.content))
                self._pendiente = self.respuesta_post
            else:
                params = dict(request.url.params)
                self.gets.append(params)
                self._pendiente = {"ok": True, "fecha": params.get("disponibilidad"),
                                   "tratamiento": params.get("tratamiento"),
                                   "bloqueadas": self.bloqueadas}
            # Apps Script siempre redirige a googleusercontent con el resultado
            return httpx.Response(302, headers={"Location": "https://script.googleusercontent.com/echo?x=1"})
        if request.url.host == "script.googleusercontent.com":
            assert request.method == "GET", "tras el 302 el cliente debe hacer GET"
            return httpx.Response(200, json=self._pendiente)
        return httpx.Response(404)

    @property
    def transporte(self):
        return httpx.MockTransport(self)


# ------------------------------------------------------------------ Graph API falsa
class GraphFalsa:
    def __init__(self):
        self.enviados: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer TOKEN"
        self.enviados.append(json.loads(request.content))
        return httpx.Response(200, json={"messages": [{"id": "wamid.X"}]})

    @property
    def transporte(self):
        return httpx.MockTransport(self)


# ------------------------------------------------------------------- Claude falso
def texto(t: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=t)], stop_reason="end_turn",
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=0))


def herramienta(nombre: str, entrada: dict, id_="tu_1", previo: str | None = None):
    bloques = []
    if previo:
        bloques.append(SimpleNamespace(type="text", text=previo))
    bloques.append(SimpleNamespace(type="tool_use", id=id_, name=nombre, input=entrada))
    return SimpleNamespace(content=bloques, stop_reason="tool_use", usage=None)


class ClaudeFalso:
    """Devuelve respuestas guionizadas y guarda cada llamada para inspeccionarla."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.llamadas: list[dict] = []

    def __call__(self, **kwargs):
        # copia profunda para ver el historial tal y como estaba en esa llamada
        self.llamadas.append(json.loads(json.dumps(kwargs, default=str)))
        if not self.guion:
            raise AssertionError("Claude falso sin más respuestas en el guion")
        r = self.guion.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


# -------------------------------------------------------------------- fixtures
@pytest.fixture
def config():
    return Config(
        anthropic_api_key="falsa",
        apps_script_url=APPS_URL,
        whatsapp_token="TOKEN",
        whatsapp_phone_number_id="123456",
        whatsapp_verify_token="verifica-innovae",
        whatsapp_app_secret=APP_SECRET,
        origenes_permitidos=["https://newdevelop20.github.io"],
    )


def firmar(cuerpo: bytes) -> str:
    return "sha256=" + hmac.new(APP_SECRET.encode(), cuerpo, hashlib.sha256).hexdigest()

"""Usa el SDK OFICIAL de Anthropic contra una API simulada: comprueba que lo que
enviamos tiene el formato correcto y que sabemos leer sus respuestas reales."""
import json

import anthropic
import httpx2
from conftest import APPS_URL, AppsScriptFalso, proximo_dia

from app.agente import Agente
from app.config import Config
from app.herramientas import AppsScriptCliente, Herramientas
from app.sesiones import AlmacenSesiones


def test_bucle_con_sdk_oficial():
    fecha = proximo_dia(2)
    peticiones = []
    respuestas = [
        {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
         "stop_reason": "tool_use", "stop_sequence": None,
         "usage": {"input_tokens": 3000, "output_tokens": 40, "cache_read_input_tokens": 2900},
         "content": [{"type": "text", "text": "Miro la agenda."},
                     {"type": "tool_use", "id": "toolu_01", "name": "consultar_disponibilidad",
                      "input": {"fecha": fecha, "tratamiento": "Dermapen"}}]},
        {"id": "msg_2", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
         "stop_reason": "end_turn", "stop_sequence": None,
         "usage": {"input_tokens": 3100, "output_tokens": 30},
         "content": [{"type": "text", "text": "Hay hueco a las 10:00."}]},
    ]

    def api(request: httpx2.Request):
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "sk-ant-prueba"
        peticiones.append(json.loads(request.content))
        return httpx2.Response(200, json=respuestas.pop(0))

    sdk = anthropic.Anthropic(api_key="sk-ant-prueba", base_url="https://api.anthropic.test",
                              http_client=httpx2.Client(transport=httpx2.MockTransport(api)))
    apps = AppsScriptFalso()
    agente = Agente(Config(anthropic_api_key="x"), sdk.messages.create,
                    Herramientas(AppsScriptCliente(APPS_URL, transport=apps.transporte)), AlmacenSesiones())

    assert agente.responder("web:sdk", "¿Hay hueco para Dermapen?") == "Hay hueco a las 10:00."

    segunda = peticiones[1]
    assert segunda["model"] == "claude-haiku-5-5"
    assert segunda["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert segunda["messages"][1]["content"][1] == {
        "type": "tool_use", "id": "toolu_01", "name": "consultar_disponibilidad",
        "input": {"fecha": fecha, "tratamiento": "Dermapen"}}
    resultado = segunda["messages"][2]["content"][0]
    assert resultado["type"] == "tool_result" and resultado["tool_use_id"] == "toolu_01"
    assert json.loads(resultado["content"])["horas_libres"][0] == "10:00"

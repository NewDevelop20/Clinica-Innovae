from conftest import APPS_URL, AppsScriptFalso, ClaudeFalso, herramienta, proximo_dia, texto

from app.agente import MENSAJE_ERROR, Agente
from app.herramientas import AppsScriptCliente, Contexto, Herramientas
from app.prompt import bloques_sistema
from app.sesiones import AlmacenSesiones, recortar


def montar(config, guion, falso=None):
    falso = falso or AppsScriptFalso()
    claude = ClaudeFalso(guion)
    agente = Agente(config, claude, Herramientas(AppsScriptCliente(APPS_URL, transport=falso.transporte)),
                    AlmacenSesiones())
    return agente, claude, falso


def roles_alternan(mensajes):
    return all(a["role"] != b["role"] for a, b in zip(mensajes, mensajes[1:]))


def test_flujo_completo_de_reserva(config):
    fecha = proximo_dia(3)
    guion = [
        # turno 1: consulta disponibilidad y propone horas
        herramienta("consultar_disponibilidad", {"fecha": fecha, "tratamiento": "Limpieza Facial"},
                    previo="Voy a mirar la agenda."),
        texto("Tengo libres las 10:00, 10:30 y 11:00. ¿Cuál prefiere?"),
        # turno 2: el cliente confirma -> crea la solicitud
        herramienta("crear_solicitud_reserva", {
            "tratamiento": "Limpieza Facial", "fecha": fecha, "hora": "10:30", "nombre": "Ana López",
            "telefono": "600111222", "cliente_ha_confirmado": True}, id_="tu_2"),
        texto("¡Hecho! Su solicitud AB12CD34 queda pendiente de confirmar por la clínica."),
    ]
    agente, claude, falso = montar(config, guion)

    r1 = agente.responder("web:s1", "Quiero una limpieza facial el jueves")
    assert "10:30" in r1
    r2 = agente.responder("web:s1", "Sí, a las 10:30. Ana López, 600111222")
    assert "AB12CD34" in r2
    assert falso.posts[0]["hora"] == "10:30"

    # El historial que se envía a Claude es válido: roles alternos y cada tool_use con su tool_result
    ultimo = claude.llamadas[-1]["messages"]
    assert roles_alternan(ultimo)
    usos = [b["id"] for m in ultimo if m["role"] == "assistant" and isinstance(m["content"], list)
            for b in m["content"] if b["type"] == "tool_use"]
    resultados = [b["tool_use_id"] for m in ultimo if m["role"] == "user" and isinstance(m["content"], list)
                  for b in m["content"] if b["type"] == "tool_result"]
    assert usos == resultados == ["tu_1", "tu_2"]

    # Instrucciones cacheadas + bloque variable con la fecha
    sistema = claude.llamadas[0]["system"]
    assert sistema[0]["cache_control"] == {"type": "ephemeral"}
    assert "Hora de España" in sistema[1]["text"] or "hora de España" in sistema[1]["text"]
    assert {t["name"] for t in claude.llamadas[0]["tools"]} == {
        "consultar_profesionales", "consultar_disponibilidad", "crear_solicitud_reserva", "derivar_a_persona"}


def test_error_de_claude_no_guarda_historial_roto(config):
    agente, _, _ = montar(config, [RuntimeError("caída de la API")])
    assert agente.responder("web:s2", "hola") == MENSAJE_ERROR
    assert agente.sesiones.obtener("web:s2") == []


def test_limite_de_herramientas(config):
    config.max_iteraciones_herramientas = 2
    bucle = [herramienta("derivar_a_persona", {"motivo": "x"}, id_=f"t{i}") for i in range(3)]
    agente, _, _ = montar(config, bucle)
    assert agente.responder("web:s3", "hola") == MENSAJE_ERROR
    hist = agente.sesiones.obtener("web:s3")
    assert roles_alternan(hist) and hist[-1]["role"] == "assistant"
    assert hist[-1]["content"][0]["type"] == "text"  # no queda un tool_use sin respuesta


def test_sesiones_separadas(config):
    agente, claude, _ = montar(config, [texto("A"), texto("B")])
    agente.responder("web:uno", "hola")
    agente.responder("web:dos", "hola")
    assert len(claude.llamadas[1]["messages"]) == 1


def test_recortar_no_parte_herramientas():
    hist = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "a", "name": "x", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "a", "content": "{}"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "r"}]},
        {"role": "user", "content": "2"},
        {"role": "assistant", "content": [{"type": "text", "text": "r2"}]},
    ]
    r = recortar(hist, 4)
    assert r[0] == {"role": "user", "content": "2"}


def test_prompt_igual_en_ambos_canales_salvo_bloque_variable():
    web, wa = bloques_sistema("web"), bloques_sistema("whatsapp")
    assert web[0]["text"] == wa[0]["text"]       # mismas instrucciones -> misma caché
    assert "un asterisco" in wa[1]["text"] and "WhatsApp" in wa[1]["text"]
    assert "Limpieza Facial" in web[0]["text"]

import json

from conftest import AppsScriptFalso, ClaudeFalso, GraphFalsa, firmar, herramienta, proximo_dia, texto
from fastapi.testclient import TestClient

from app.config import Config
from app.main import crear_app
from app.whatsapp import adaptar_formato, trocear

SESION = "abc123def456"


def cliente(config, guion=(), apps=None, graph=None, llm="auto"):
    apps = apps or AppsScriptFalso()
    graph = graph or GraphFalsa()
    claude = ClaudeFalso(guion) if llm == "auto" else llm
    app = crear_app(config, llm=claude, transporte_apps_script=apps.transporte,
                    transporte_whatsapp=graph.transporte)
    return TestClient(app), claude, apps, graph


# ------------------------------------------------------------------------ web
def test_health(config):
    c, *_ = cliente(config)
    j = c.get("/health").json()
    assert j["ok"] and j["reservas"] == "conectadas" and j["whatsapp"] == "configurado"


def test_chat_web(config):
    c, claude, *_ = cliente(config, [texto("Abrimos de lunes a viernes.")])
    r = c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "¿Horario?"},
               headers={"Origin": "https://newdevelop20.github.io"})
    assert r.status_code == 200 and r.json()["respuesta"] == "Abrimos de lunes a viernes."
    assert r.headers["access-control-allow-origin"] == "https://newdevelop20.github.io"
    assert "Canal actual: web" in claude.llamadas[0]["system"][1]["text"]


def test_cors_bloquea_otros_origenes(config):
    c, *_ = cliente(config)
    r = c.options("/api/chat", headers={"Origin": "https://malicioso.example",
                                        "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers


def test_chat_valida_entrada(config):
    c, *_ = cliente(config)
    assert c.post("/api/chat", json={"sesion_id": "x", "mensaje": "hola"}).status_code == 400
    assert c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "   "}).status_code == 400
    largo = c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "a" * 2000}).json()
    assert "demasiado largo" in largo["respuesta"]


def test_sin_api_key_responde_503(config):
    c, *_ = cliente(Config(), llm=None)
    r = c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "hola"})
    assert r.status_code == 503
    assert c.get("/health").json()["ia"] == "sin API key"


def test_limite_de_mensajes(config):
    config.max_mensajes_por_ventana = 2
    c, *_ = cliente(config, [texto("1"), texto("2")])
    for _ in range(2):
        assert c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "hola"}).status_code == 200
    assert c.post("/api/chat", json={"sesion_id": SESION, "mensaje": "hola"}).status_code == 429


def test_widget_y_demo_se_sirven(config):
    c, *_ = cliente(config)
    js = c.get("/widget/innovae-chat.js")
    assert js.status_code == 200 and "attachShadow" in js.text
    assert "innovae-chat.js" in c.get("/demo").text


# ------------------------------------------------------------------- WhatsApp
def webhook(texto_msg="Hola", id_="wamid.1", tipo="text"):
    msg = {"from": "34600999888", "id": id_, "timestamp": "1", "type": tipo}
    if tipo == "text":
        msg["text"] = {"body": texto_msg}
    return {"object": "whatsapp_business_account", "entry": [{"id": "1", "changes": [{
        "field": "messages", "value": {"messaging_product": "whatsapp",
                                       "metadata": {"phone_number_id": "123456"},
                                       "contacts": [{"wa_id": "34600999888"}], "messages": [msg]}}]}]}


def post_firmado(c, payload, firma=None):
    cuerpo = json.dumps(payload).encode()
    return c.post("/webhook/whatsapp", content=cuerpo,
                  headers={"Content-Type": "application/json",
                           "X-Hub-Signature-256": firma or firmar(cuerpo)})


def test_verificacion_de_meta(config):
    c, *_ = cliente(config)
    ok = c.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "verifica-innovae",
                                            "hub.challenge": "1158201444"})
    assert ok.status_code == 200 and ok.text == "1158201444"
    mal = c.get("/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "otro",
                                             "hub.challenge": "1"})
    assert mal.status_code == 403


def test_whatsapp_responde_con_el_mismo_cerebro(config):
    c, claude, _, graph = cliente(config, [texto("**Hola** 👋 ¿En qué le ayudo?")])
    assert post_firmado(c, webhook("Hola")).status_code == 200
    assert graph.enviados == [{"messaging_product": "whatsapp", "recipient_type": "individual",
                               "to": "34600999888", "type": "text",
                               "text": {"preview_url": False, "body": "*Hola* 👋 ¿En qué le ayudo?"}}]
    sistema = claude.llamadas[0]["system"]
    assert "Canal actual: whatsapp" in sistema[1]["text"]


def test_whatsapp_reserva_con_su_numero(config):
    fecha = proximo_dia(4)
    guion = [herramienta("crear_solicitud_reserva", {"tratamiento": "Presoterapia", "fecha": fecha,
                                                     "hora": "17:00", "nombre": "Luis Pérez",
                                                     "cliente_ha_confirmado": True}),
             texto("Solicitud registrada.")]
    c, _, apps, graph = cliente(config, guion)
    post_firmado(c, webhook("Sí, confirmo"))
    assert apps.posts[0]["telefono"] == "34600999888"
    assert graph.enviados[0]["text"]["body"] == "Solicitud registrada."


def test_whatsapp_firma_incorrecta(config):
    c, _, _, graph = cliente(config)
    assert post_firmado(c, webhook(), firma="sha256=deadbeef").status_code == 403
    assert graph.enviados == []


def test_whatsapp_ignora_reintentos_y_estados(config):
    c, claude, _, graph = cliente(config, [texto("Respuesta única")])
    post_firmado(c, webhook(id_="wamid.repetido"))
    post_firmado(c, webhook(id_="wamid.repetido"))
    estados = {"entry": [{"changes": [{"value": {"statuses": [{"id": "wamid.x", "status": "read"}]}}]}]}
    assert post_firmado(c, estados).status_code == 200
    assert len(claude.llamadas) == 1 and len(graph.enviados) == 1


def test_whatsapp_audio_pide_texto(config):
    c, claude, _, graph = cliente(config)
    post_firmado(c, webhook(tipo="audio"))
    assert claude.llamadas == [] and "texto" in graph.enviados[0]["text"]["body"]


def test_formato_whatsapp():
    assert adaptar_formato("## Título\n**negrita** y [web](https://x.es)") == "Título\n*negrita* y web: https://x.es"
    partes = trocear("a" * 5000 + "\n\n" + "b" * 10)
    assert all(len(p) <= 4000 for p in partes) and "".join(partes).count("a") == 5000


# --------------------------------------------------------------- modo simulado
def test_modo_simulado_consulta_la_agenda_real():
    from app.agente import ClienteSimulado

    cfg = Config(modo_simulado=True, apps_script_url="https://script.google.com/macros/s/TEST/exec")
    apps = AppsScriptFalso(bloqueadas=["10:00"])
    c, *_ = cliente(cfg, apps=apps, llm=ClienteSimulado())
    fecha = proximo_dia(1)
    r = c.post("/api/chat", json={"sesion_id": SESION, "mensaje": f"Limpieza Facial {fecha}"}).json()
    assert r["respuesta"].startswith("[SIMULADO] Limpieza Facial") and "10:30" in r["respuesta"]
    assert "10:00," not in r["respuesta"]
    assert c.get("/health").json()["ia"] == "simulada"

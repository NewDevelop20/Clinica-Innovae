import json
from pathlib import Path
from conftest import texto, AppsScriptFalso, firmar
from test_api import cliente, post_firmado, webhook, SESION
from app.whatsapp import firma_valida
from app.herramientas import AppsScriptCliente, Contexto, Herramientas
from app.conocimiento import tratamientos


def test_firma_obligatoria_incluso_sin_secreto():
    assert not firma_valida(b'{}', None, '')
    assert not firma_valida(b'{}', 'sha256=x', '')


def test_whatsapp_no_acepta_configuracion_incompleta(config):
    config.whatsapp_app_secret = ''
    c, _, _, graph = cliente(config, [texto('hola')])
    assert c.post('/webhook/whatsapp', json=webhook()).status_code == 503
    assert not graph.enviados
    assert c.get('/health').json()['whatsapp'] == 'sin credenciales'


def test_whatsapp_ignora_otro_numero(config):
    c, claude, _, graph = cliente(config)
    payload = webhook()
    payload['entry'][0]['changes'][0]['value']['metadata']['phone_number_id'] = 'otro'
    assert post_firmado(c, payload).status_code == 200
    assert not claude.llamadas and not graph.enviados


def test_whatsapp_json_invalido(config):
    c, *_ = cliente(config)
    cuerpo = b'[]'
    assert c.post('/webhook/whatsapp', content=cuerpo,
                  headers={'X-Hub-Signature-256': firmar(cuerpo)}).status_code == 400


def test_post_origen_no_permitido_no_llama_ia(config):
    c, claude, *_ = cliente(config, [texto('x')])
    r = c.post('/api/chat', json={'sesion_id': SESION, 'mensaje': 'hola'},
               headers={'Origin': 'https://otro.example'})
    assert r.status_code == 403 and not claude.llamadas


def test_limite_ip_no_se_elude_cambiando_sesion(config):
    config.max_mensajes_por_ventana = 2
    c, *_ = cliente(config, [texto('1'), texto('2')])
    for sid in ['session_1', 'session_2']:
        assert c.post('/api/chat', json={'sesion_id': sid, 'mensaje': 'hola'}).status_code == 200
    assert c.post('/api/chat', json={'sesion_id': 'session_3', 'mensaje': 'hola'}).status_code == 429


def test_confirmacion_no_acepta_texto_false():
    apps = AppsScriptFalso()
    h = Herramientas(AppsScriptCliente('https://script.google.com/macros/s/TEST/exec', transport=apps.transporte))
    r = h.crear_solicitud_reserva({'cliente_ha_confirmado': 'false'}, Contexto())
    assert not r['ok'] and not apps.posts


def test_tratamientos_coinciden_con_formulario():
    import re
    web = Path(__file__).resolve().parents[2]
    html = (web / 'index.html').read_text()
    select = re.search(r'<select id="r-tratamiento"[\s\S]*?</select>', html)[0]
    opciones = re.findall(r'<option>([^<]+)</option>', select)
    assert set(tratamientos()) <= set(opciones)
    datos = json.loads((web / 'assets/chatbot/conocimiento.json').read_text())
    assert sum(a['tipo'] == 'tratamiento' for a in datos['articulos']) == 26
    assert sum(a['tipo'] == 'producto' for a in datos['articulos']) == 11
    assert 'PENDIENTE' not in json.dumps(datos)

import json
from types import SimpleNamespace

import comprobar_servicios as preflight
from app.config import Config
from app.herramientas import AppsScriptCliente
from conftest import AppsScriptFalso, herramienta, proximo_dia, texto
from test_api import cliente, SESION


def test_preflight_sin_clave_ni_agenda_no_contacta_proveedores():
    r = preflight.comprobar(Config(), ia=True, agenda=True)
    assert r['ia'] == 'pendiente de ANTHROPIC_API_KEY'
    assert r['agenda'] == 'pendiente de APPS_SCRIPT_URL'
    assert r['crea_reservas'] is False


def test_preflight_agenda_solo_lee(monkeypatch):
    apps = AppsScriptFalso()
    monkeypatch.setattr(preflight, 'AppsScriptCliente', lambda url: AppsScriptCliente(url, transport=apps.transporte))
    r = preflight.comprobar(Config(apps_script_url='https://script.google.com/macros/s/TEST/exec'), agenda=True)
    assert r['agenda'] == 'catálogo y disponibilidad públicos comprobados'
    assert len(apps.gets) == 2 and apps.posts == []


def test_preflight_ia_es_una_llamada_sin_clave_en_la_salida(monkeypatch):
    calls = []
    class SDK:
        def __init__(self, **kwargs):
            assert kwargs['max_retries'] == 0
            self.messages = SimpleNamespace(create=self.crear)
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def crear(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(model='modelo-de-prueba', usage=SimpleNamespace(input_tokens=8, output_tokens=1))
    import anthropic
    monkeypatch.setattr(anthropic, 'Anthropic', SDK)
    clave = 'secreto-ficticio-no-publicar'
    r = preflight.comprobar(Config(anthropic_api_key=clave), ia=True)
    assert r['ia'] == 'respuesta real recibida'
    assert len(calls) == 1 and calls[0]['max_tokens'] == 16
    assert clave not in json.dumps(r)


def test_reserva_web_completa_simulada_espera_confirmacion_y_mantiene_profesional(config):
    fecha = proximo_dia(1)
    datos = {'tratamiento': 'Limpieza Facial', 'profesional': 'marta-jimenez', 'fecha': fecha,
             'hora': '10:00', 'nombre': 'Prueba Web', 'telefono': '600123456',
             'email': 'prueba@example.com', 'cliente_ha_confirmado': True}
    guion = [herramienta('consultar_profesionales', {}),
             herramienta('consultar_disponibilidad', {'fecha': fecha, 'tratamiento': 'Limpieza Facial', 'profesional': 'marta-jimenez'}),
             texto('Hay disponibilidad a las 10:00. ¿Cuál es su nombre y teléfono?'),
             texto('Resumen: Limpieza Facial con Marta a las 10:00. ¿Confirma y consiente el tratamiento de datos para gestionar la cita?'),
             herramienta('crear_solicitud_reserva', datos),
             texto('Solicitud #AB12CD34 registrada, pendiente de confirmación de la clínica.')]
    c, _, apps, _ = cliente(config, guion)
    for mensaje in ['Quiero una limpieza con Marta', 'Prueba Web, 600123456, prueba@example.com']:
        r = c.post('/api/chat', json={'sesion_id': SESION, 'mensaje': mensaje})
        assert r.status_code == 200 and apps.posts == []
    r = c.post('/api/chat', json={'sesion_id': SESION, 'mensaje': 'Sí, confirmo y consiento'})
    assert 'pendiente' in r.json()['respuesta']
    assert len(apps.posts) == 1
    assert apps.posts[0]['profesional'] == 'marta-jimenez'
    assert apps.posts[0]['email'] == 'prueba@example.com'

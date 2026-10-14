from datetime import date, datetime

from conftest import APPS_URL, AppsScriptFalso, proximo_dia

from app import horario
from app.conocimiento import texto_conocimiento, tratamiento_oficial, tratamientos
from app.herramientas import AppsScriptCliente, Contexto, Herramientas


def herramientas_con(falso: AppsScriptFalso, url=APPS_URL) -> Herramientas:
    return Herramientas(AppsScriptCliente(url, transport=falso.transporte))


# ----------------------------------------------------------------- conocimiento
def test_conocimiento_carga_26_tratamientos_y_quita_notas():
    assert len(tratamientos()) == 26  # 25 de la web + primera consulta
    assert "Limpieza Facial" in tratamientos()
    assert "PENDIENTE" not in texto_conocimiento()  # los comentarios no llegan al modelo
    assert "661 73 48 70" in texto_conocimiento()


def test_nombre_de_tratamiento_tolerante():
    assert tratamiento_oficial("limpieza facial") == "Limpieza Facial"
    assert tratamiento_oficial("RADIOFRECUENCIA") == "Radiofrecuencia"
    assert tratamiento_oficial("blumed") == "Eliminación de Manchas y Lesiones (Blumed)"
    assert tratamiento_oficial("depilación") is None  # ambiguo: SHR o IPL
    assert tratamiento_oficial("pizza") is None


# ---------------------------------------------------------------------- horario
def test_horas_de_un_lunes_respetan_cierre_y_duracion():
    lunes = date.fromisoformat(proximo_dia(0))
    horas = horario.horas_posibles(lunes, datetime(2000, 1, 1, tzinfo=horario.ZONA))
    assert horas[0] == "10:00" and "12:30" in horas and "13:00" not in horas  # 13:00+60 > 13:30
    assert "16:30" in horas and "19:30" in horas and "20:00" not in horas


def test_sabado_y_domingo():
    sabado = date.fromisoformat(proximo_dia(5))
    assert horario.horas_posibles(sabado, datetime(2000, 1, 1, tzinfo=horario.ZONA)) == \
        ["10:30", "11:00", "11:30", "12:00"]
    domingo = date.fromordinal(sabado.toordinal() + 1)
    assert horario.motivo_fecha_no_valida(domingo) == "La clínica cierra ese día."


def test_hoy_solo_horas_con_margen():
    lunes = date.fromisoformat(proximo_dia(0))
    momento = datetime(lunes.year, lunes.month, lunes.day, 11, 10, tzinfo=horario.ZONA)
    assert horario.horas_posibles(lunes, momento)[0] == "12:30"


# ----------------------------------------------------------------- disponibilidad
def test_disponibilidad_quita_horas_bloqueadas_y_sigue_redireccion():
    falso = AppsScriptFalso(bloqueadas=["10:00", "10:15", "17:00"])
    r = herramientas_con(falso).consultar_disponibilidad(proximo_dia(1), "limpieza facial")
    assert r["ok"] and r["tratamiento"] == "Limpieza Facial"
    assert "10:00" not in r["horas_libres"] and "17:00" not in r["horas_libres"]
    assert "10:30" in r["horas_libres"]
    assert falso.gets[0]["tratamiento"] == "Limpieza Facial"  # nombre oficial hacia Code.gs


def test_disponibilidad_errores_claros():
    h = herramientas_con(AppsScriptFalso())
    assert "no reconocido" in h.consultar_disponibilidad(proximo_dia(1), "pizza")["error"]
    assert "cierra" in h.consultar_disponibilidad(
        date.fromordinal(date.fromisoformat(proximo_dia(5)).toordinal() + 1).isoformat(),
        "Limpieza Facial")["error"]
    assert "pasado" in h.consultar_disponibilidad("2020-01-01", "Limpieza Facial")["error"]


def test_sin_apps_script_configurado_da_alternativa():
    r = herramientas_con(AppsScriptFalso(), url="").consultar_disponibilidad(proximo_dia(1), "Limpieza Facial")
    assert not r["ok"] and r["alternativa"]["telefono"] == "661 73 48 70"


def test_fallo_de_red_no_rompe():
    h = herramientas_con(AppsScriptFalso(fallo_red=True))
    r = h.ejecutar("consultar_disponibilidad", {"fecha": proximo_dia(1), "tratamiento": "Dermapen"}, Contexto())
    assert not r["ok"] and "no responde" in r["error"]


# ------------------------------------------------------------------------ reserva
def datos_reserva(**extra):
    base = {"tratamiento": "Dermapen", "fecha": proximo_dia(2), "hora": "11:00",
            "nombre": "Ana López", "telefono": "600 111 222", "email": "ana@example.com",
            "primera_visita": True, "comentarios": "Prefiere mañanas", "cliente_ha_confirmado": True}
    base.update(extra)
    return base


def test_reserva_envia_los_campos_que_espera_code_gs():
    falso = AppsScriptFalso()
    r = herramientas_con(falso).ejecutar("crear_solicitud_reserva", datos_reserva(), Contexto(canal="web"))
    assert r["ok"] and r["id"] == "AB12CD34" and "PENDIENTE" in r["estado"]
    enviado = falso.posts[0]
    assert enviado == {
        "nombre": "Ana López", "telefono": "600111222", "email": "ana@example.com",
        "tratamiento": "Dermapen", "fecha": datos_reserva()["fecha"], "hora": "11:00",
        "primeraVisita": "true", "comentarios": "[Chatbot web] Prefiere mañanas", "website": "",
    }


def test_reserva_por_whatsapp_usa_el_numero_si_no_dan_otro():
    falso = AppsScriptFalso()
    r = herramientas_con(falso).ejecutar("crear_solicitud_reserva", datos_reserva(telefono=""),
                                         Contexto(canal="whatsapp", telefono="34600999888"))
    assert r["ok"]
    assert falso.posts[0]["telefono"] == "34600999888"
    assert falso.posts[0]["comentarios"].startswith("[Chatbot WhatsApp]")


def test_reserva_exige_confirmacion_y_datos_validos():
    falso = AppsScriptFalso()
    h = herramientas_con(falso)
    assert "confirmación" in h.ejecutar("crear_solicitud_reserva",
                                        datos_reserva(cliente_ha_confirmado=False), Contexto())["error"]
    r = h.ejecutar("crear_solicitud_reserva", datos_reserva(telefono="123", email="no-es-email"), Contexto())
    assert "9 dígitos" in r["error"] and "email" in r["error"]
    assert falso.posts == []  # nada llegó al calendario


def test_reserva_rechaza_hora_ya_ocupada():
    falso = AppsScriptFalso(bloqueadas=["11:00"])
    r = herramientas_con(falso).ejecutar("crear_solicitud_reserva", datos_reserva(), Contexto())
    assert not r["ok"] and "ya no están libres" in r["error"] and "11:00" not in r["horas_libres"]
    assert falso.posts == []


def test_reserva_propaga_el_error_de_code_gs():
    falso = AppsScriptFalso(respuesta_post={"ok": False, "motivo": "mismo_tratamiento",
                                            "error": "Ese tratamiento ya está reservado a esa hora."})
    r = herramientas_con(falso).ejecutar("crear_solicitud_reserva", datos_reserva(), Contexto())
    assert not r["ok"] and r["motivo"] == "mismo_tratamiento"

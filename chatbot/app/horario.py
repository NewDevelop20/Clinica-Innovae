"""Horario de apertura y franjas que se pueden ofrecer.

Code.gs sabe qué horas están OCUPADAS; aquí decidimos qué horas existen
(la clínica abierta y que la cita de ~60 min quepa antes del cierre).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("Europe/Madrid")
DURACION_MIN = 60   # igual que CONFIG.DURACION_MIN en Code.gs
PASO_MIN = 30       # cada cuánto se ofrecen horas
DIAS_MAX_ANTELACION = 90

# weekday(): 0 = lunes ... 6 = domingo
HORARIO: dict[int, list[tuple[str, str]]] = {
    0: [("10:00", "13:30"), ("16:30", "20:30")],
    1: [("10:00", "13:30"), ("16:30", "20:30")],
    2: [("10:00", "13:30"), ("16:30", "20:30")],
    3: [("10:00", "13:30"), ("16:30", "20:30")],
    4: [("10:00", "13:30"), ("16:30", "20:30")],
    5: [("10:30", "13:00")],
    6: [],
}

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def ahora() -> datetime:
    return datetime.now(ZONA)


def _minutos(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutos: int) -> str:
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def parsear_fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(str(texto).strip()[:10])
    except ValueError:
        return None


def fecha_legible(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def horas_posibles(d: date, momento: datetime | None = None) -> list[str]:
    """Horas de inicio en las que cabe una cita ese día (sin mirar ocupación)."""
    momento = momento or ahora()
    horas: list[str] = []
    for apertura, cierre in HORARIO[d.weekday()]:
        m = _minutos(apertura)
        while m + DURACION_MIN <= _minutos(cierre):
            horas.append(_hhmm(m))
            m += PASO_MIN
    if d == momento.date():  # hoy: solo horas con al menos 1 h de margen
        limite = momento.hour * 60 + momento.minute + 60
        horas = [h for h in horas if _minutos(h) >= limite]
    return horas


def motivo_fecha_no_valida(d: date, momento: datetime | None = None) -> str | None:
    momento = momento or ahora()
    if d < momento.date():
        return "Esa fecha ya ha pasado."
    if d > momento.date() + timedelta(days=DIAS_MAX_ANTELACION):
        return f"Solo se puede reservar con hasta {DIAS_MAX_ANTELACION} días de antelación."
    if not HORARIO[d.weekday()]:
        return "La clínica cierra ese día."
    return None

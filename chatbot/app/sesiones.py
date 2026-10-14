"""Memoria de conversaciones, límite de mensajes y deduplicado (en memoria).

Suficiente para el MVP con UNA instancia en Cloud Run (--max-instances=1).
Si algún día hay más tráfico, se cambia por Firestore/Redis sin tocar el resto.
"""
from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque


class AlmacenSesiones:
    def __init__(self, max_mensajes: int = 30, caducidad_s: int = 4 * 3600, max_sesiones: int = 5000):
        self.max_mensajes = max_mensajes
        self.caducidad_s = caducidad_s
        self.max_sesiones = max_sesiones
        self._datos: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()
        self._lock = threading.Lock()
        # Un número fijo de locks evita fugas al recibir muchos IDs nuevos y
        # mantiene el mismo lock aunque la conversación caduque o se expulse.
        self._locks_sesion = [threading.Lock() for _ in range(256)]

    def lock_de(self, sesion_id: str) -> threading.Lock:
        """Un lock por conversación: dos mensajes seguidos no se procesan a la vez."""
        return self._locks_sesion[hash(sesion_id) % len(self._locks_sesion)]

    def obtener(self, sesion_id: str) -> list[dict]:
        with self._lock:
            self._purgar()
            item = self._datos.get(sesion_id)
            return list(item[1]) if item else []

    def guardar(self, sesion_id: str, mensajes: list[dict]) -> None:
        with self._lock:
            self._datos[sesion_id] = (time.time(), recortar(mensajes, self.max_mensajes))
            self._datos.move_to_end(sesion_id)
            while len(self._datos) > self.max_sesiones:
                viejo, _ = self._datos.popitem(last=False)

    def borrar(self, sesion_id: str) -> None:
        with self._lock:
            self._datos.pop(sesion_id, None)

    def _purgar(self) -> None:
        limite = time.time() - self.caducidad_s
        for sid in [s for s, (t, _) in self._datos.items() if t < limite]:
            self._datos.pop(sid, None)


def _es_inicio_de_turno(m: dict) -> bool:
    """Mensaje del usuario con texto (no un tool_result): punto seguro para cortar."""
    if m.get("role") != "user":
        return False
    c = m.get("content")
    return isinstance(c, str) or (
        isinstance(c, list) and all(b.get("type") == "text" for b in c)
    )


def recortar(mensajes: list[dict], maximo: int) -> list[dict]:
    """Deja los últimos `maximo` mensajes sin partir un par tool_use/tool_result."""
    if len(mensajes) <= maximo:
        return mensajes
    recortado = mensajes[-maximo:]
    while recortado and not _es_inicio_de_turno(recortado[0]):
        recortado = recortado[1:]
    return recortado


class LimitadorMensajes:
    """Máximo N mensajes por clave (sesión) en una ventana de tiempo."""

    def __init__(self, maximo: int, ventana_s: int):
        self.maximo, self.ventana_s = maximo, ventana_s
        self._marcas: dict[str, deque] = {}
        self._lock = threading.Lock()

    def permitir(self, clave: str) -> bool:
        ahora = time.time()
        with self._lock:
            d = self._marcas.setdefault(clave, deque())
            while d and d[0] < ahora - self.ventana_s:
                d.popleft()
            if len(d) >= self.maximo:
                return False
            d.append(ahora)
            if len(self._marcas) > 20000:  # evita crecer sin límite
                self._marcas = {k: v for k, v in self._marcas.items()
                                if v and v[-1] >= ahora - self.ventana_s}
                if len(self._marcas) > 20000:
                    self._marcas.pop(clave, None)
                    return False
            return True


class Deduplicador:
    """Meta puede reenviar el mismo webhook: recordamos los últimos IDs vistos."""

    def __init__(self, capacidad: int = 2000):
        self._vistos: OrderedDict[str, None] = OrderedDict()
        self._cap = capacidad
        self._lock = threading.Lock()

    def ya_visto(self, id_: str) -> bool:
        with self._lock:
            if id_ in self._vistos:
                return True
            self._vistos[id_] = None
            if len(self._vistos) > self._cap:
                self._vistos.popitem(last=False)
            return False

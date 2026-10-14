"""Carga el conocimiento de la clínica desde conocimiento/*.md.

- Los comentarios HTML (<!-- ... -->) se eliminan: son notas internas.
- De tratamientos.md se sacan los nombres oficiales (encabezados "###"),
  que se usan para validar el tratamiento antes de crear una reserva.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from .config import CARPETA_CONOCIMIENTO

_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
ORDEN = ["clinica.md", "tratamientos.md", "productos.md"]


def normalizar(texto: str) -> str:
    """Igual que normalizar_() de Code.gs: minúsculas, sin tildes, espacios simples."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t).strip()


def _leer(ruta: Path) -> str:
    texto = _COMENTARIO.sub("", ruta.read_text(encoding="utf-8"))
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


@lru_cache(maxsize=1)
def texto_conocimiento(carpeta: Path = CARPETA_CONOCIMIENTO) -> str:
    partes = []
    nombres = ORDEN + sorted(p.name for p in carpeta.glob("*.md") if p.name not in ORDEN)
    for nombre in nombres:
        ruta = carpeta / nombre
        if ruta.exists():
            partes.append(_leer(ruta))
    return "\n\n---\n\n".join(partes)


@lru_cache(maxsize=1)
def tratamientos(carpeta: Path = CARPETA_CONOCIMIENTO) -> tuple[str, ...]:
    texto = _leer(carpeta / "tratamientos.md")
    return tuple(m.strip() for m in re.findall(r"^###\s+(.+)$", texto, re.MULTILINE))


def tratamiento_oficial(nombre: str) -> str | None:
    """Devuelve el nombre oficial que coincide con `nombre` (tolerante), o None."""
    buscado = normalizar(nombre)
    if not buscado:
        return None
    oficiales = {normalizar(t): t for t in tratamientos()}
    if buscado in oficiales:
        return oficiales[buscado]
    # Coincidencia parcial única (p. ej. "blumed" -> "Eliminación de Manchas y Lesiones (Blumed)")
    parciales = [t for n, t in oficiales.items() if buscado in n or n in buscado]
    return parciales[0] if len(parciales) == 1 else None

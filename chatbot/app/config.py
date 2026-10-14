"""Configuración del chatbot, leída de variables de entorno.

Todo lo sensible (API keys, tokens) llega por entorno: nunca va en el código.
En local se puede usar un fichero .env (ver .env.example).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # .env opcional en local; en Cloud Run las variables vienen del servicio
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


def _bool(valor: str | None) -> bool:
    return str(valor or "").strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


@dataclass
class Config:
    # --- Claude -----------------------------------------------------------
    anthropic_api_key: str = ""
    modelo: str = "claude-haiku-5-5"      # barato y rápido; se cambia por entorno
    max_tokens: int = 800
    max_iteraciones_herramientas: int = 6  # tope de llamadas a herramientas por mensaje

    # Sin API key se puede probar todo el circuito con respuestas simuladas.
    modo_simulado: bool = False

    # --- Reservas (Code.gs de Apps Script) --------------------------------
    apps_script_url: str = ""              # URL /exec del Web App
    timeout_http: float = 20.0

    # --- WhatsApp Cloud API -------------------------------------------------
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""        # lo inventas tú y lo pegas también en Meta
    whatsapp_app_secret: str = ""          # para verificar la firma de Meta
    graph_api_version: str = "v21.0"

    # --- Web --------------------------------------------------------------
    origenes_permitidos: list[str] = field(default_factory=list)

    # --- Límites ------------------------------------------------------------
    max_longitud_mensaje: int = 1000
    max_mensajes_por_ventana: int = 20     # por sesión
    ventana_segundos: int = 600
    max_turnos_historial: int = 30         # mensajes que se recuerdan por conversación
    caducidad_sesion_segundos: int = 4 * 3600

    @classmethod
    def desde_entorno(cls) -> "Config":
        e = os.environ.get
        return cls(
            anthropic_api_key=e("ANTHROPIC_API_KEY", ""),
            modelo=e("ANTHROPIC_MODEL", cls.modelo),
            max_tokens=int(e("ANTHROPIC_MAX_TOKENS", cls.max_tokens)),
            modo_simulado=_bool(e("MODO_SIMULADO")),
            apps_script_url=e("APPS_SCRIPT_URL", ""),
            whatsapp_token=e("WHATSAPP_TOKEN", ""),
            whatsapp_phone_number_id=e("WHATSAPP_PHONE_NUMBER_ID", ""),
            whatsapp_verify_token=e("WHATSAPP_VERIFY_TOKEN", ""),
            whatsapp_app_secret=e("WHATSAPP_APP_SECRET", ""),
            graph_api_version=e("GRAPH_API_VERSION", cls.graph_api_version),
            origenes_permitidos=_lista(
                e(
                    "ORIGENES_PERMITIDOS",
                    "https://newdevelop20.github.io,http://localhost:8000,http://127.0.0.1:8000",
                )
            ),
        )

    @property
    def llm_disponible(self) -> bool:
        return bool(self.anthropic_api_key) or self.modo_simulado

    @property
    def whatsapp_configurado(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id
                    and self.whatsapp_app_secret and self.whatsapp_verify_token)


RAIZ = Path(__file__).resolve().parent.parent
CARPETA_CONOCIMIENTO = RAIZ / "conocimiento"

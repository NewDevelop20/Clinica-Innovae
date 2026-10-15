"""Preflight sin escrituras en Calendar. --ia hace UNA petición real a Anthropic."""
from __future__ import annotations
import argparse
import json
from datetime import timedelta
from app.config import Config
from app.herramientas import AppsScriptCliente
from app import horario


def comprobar(config: Config, ia: bool = False, agenda: bool = False) -> dict:
    salida = {"ia": "no probada", "agenda": "no probada", "crea_reservas": False}
    if ia:
        if not config.anthropic_api_key:
            salida["ia"] = "pendiente de ANTHROPIC_API_KEY"
        elif config.modo_simulado:
            salida["ia"] = "desactive MODO_SIMULADO para comprobar la clave real"
        else:
            try:
                import anthropic
                with anthropic.Anthropic(api_key=config.anthropic_api_key, timeout=30, max_retries=0) as client:
                    respuesta = client.messages.create(model=config.modelo, max_tokens=16,
                        messages=[{"role": "user", "content": "Responde únicamente OK."}])
                salida["ia"] = "respuesta real recibida"
                salida["modelo"] = respuesta.model
                salida["tokens_entrada"] = respuesta.usage.input_tokens
                salida["tokens_salida"] = respuesta.usage.output_tokens
            except Exception as error:
                # No mostrar la clave, cabeceras ni cuerpos de respuestas del proveedor.
                salida["ia"] = "fallo de conexión o configuración: " + type(error).__name__
    if agenda:
        if not config.apps_script_url:
            salida["agenda"] = "pendiente de APPS_SCRIPT_URL"
        else:
            cliente = AppsScriptCliente(config.apps_script_url)
            try:
                profesionales = cliente.profesionales()
                if not profesionales:
                    raise ValueError("Catálogo vacío")
                fecha = horario.ahora().date() + timedelta(days=2)
                while fecha.weekday() == 6:
                    fecha += timedelta(days=1)
                cliente.horas_bloqueadas(fecha.isoformat(), "Primera consulta / valoración", profesionales[0]["id"])
                salida["agenda"] = "catálogo y disponibilidad públicos comprobados"
                salida["profesionales"] = len(profesionales)
            except Exception as error:
                salida["agenda"] = "no responde con la API esperada: " + type(error).__name__
            finally:
                cliente._http.close()
    return salida


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ia", action="store_true", help="Una llamada real facturable, solo después de configurar el límite en Anthropic")
    parser.add_argument("--agenda", action="store_true", help="Solo consulta catálogo y disponibilidad; no crea citas")
    args = parser.parse_args()
    resultado = comprobar(Config.desde_entorno(), args.ia, args.agenda)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    if ((args.ia and resultado["ia"] != "respuesta real recibida") or
            (args.agenda and resultado["agenda"] != "catálogo y disponibilidad públicos comprobados")):
        raise SystemExit(1)

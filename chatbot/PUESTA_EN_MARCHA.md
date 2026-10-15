# Activar el chatbot web

La web ya incluye el widget. Mientras `assets/chatbot-config.js` tenga `api: ''`,
funciona como consulta local sin IA y no registra citas. La bienvenida distingue
este modo del modo IA; ambos muestran el límite médico, el contacto humano y la privacidad.
Los 27 nombres de `conocimiento/tratamientos.md` coinciden con el formulario,
incluidas primera valoración y «Otro / Consulta general».

## Requisitos que debe crear el titular

1. Crear una cuenta en la [consola de Anthropic](https://console.anthropic.com/)
   usando su Gmail. Es independiente de una suscripción al chat de Claude.
2. Configurar la facturación y el límite mensual de gasto para la API en esa consola.
   Para pruebas se puede elegir 5 USD y dejar desactivada la recarga automática.
   El límite aún no está configurado por este repositorio: debe guardarse en Anthropic.
3. Crear una API key para este proyecto. No enviarla por chat ni subirla a GitHub.
4. Crear un proyecto de [Google Cloud](https://console.cloud.google.com/) con facturación,
   una cuenta de servicio dedicada y un secreto `anthropic-key` en Secret Manager.
   Guardar allí la clave. No descargar ni compartir una clave JSON de Google.
5. Verificar que Apps Script permite acceso a **cualquier usuario**, sin iniciar sesión,
   y que publica la última versión de `reservas/Code.gs`. Mantener el calendario de
   pruebas y los avisos al correo personal durante la validación.

La variable de credenciales del entorno de Codex pertenece a su infraestructura;
no da acceso a la cuenta de Google del titular. No se usa para estos pasos.
El gasto de Anthropic y el de Google Cloud son independientes. Un presupuesto de
Google Cloud envía alertas; no es un tope automático de facturación. El despliegue
limita Cloud Run a una instancia y permite bajar a cero cuando no se usa.

## Prueba local con los servicios reales

Desde `chatbot`, preparar el entorno como explica README.md y guardar la clave en
`.env` local (ignorado por Git). Configurar `MODO_SIMULADO=0`, `ANTHROPIC_MODEL` y
`APPS_SCRIPT_URL`. La comprobación siguiente hace una llamada real mínima a Claude
(puede generar un pequeño cargo) y solo lecturas en la agenda:

```sh
python comprobar_servicios.py --ia --agenda
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abrir `/demo` del servidor local. Consultar horarios y productos, pedir hablar con
una persona y comprobar que las preguntas médicas se derivan a la clínica.
Para una solicitud de prueba: elegir tratamiento, profesional, fecha y hora libres;
usar un nombre ficticio y el correo personal autorizado. Revisar el resumen y el
consentimiento antes de confirmar el envío. Comprobar código, profesional, evento
amarillo y correo. La clínica aún debe aceptar o rechazar la solicitud desde el
correo; una solicitud no es una cita confirmada. Rechazarla al terminar libera el hueco.
No hacer pruebas con datos reales de pacientes.

Las pruebas automáticas usan servicios simulados. No acreditan que la clave,
la facturación, la disponibilidad real ni el correo de Google estén operativos.

## Desplegar solo la web

En Cloud Shell con el repositorio, autenticar el Gmail del titular. La cuenta de
servicio y el secreto deben existir en el proyecto. Desde `chatbot`:

```sh
export INNOVAE_PROJECT_ID='ID_DE_TU_PROYECTO'
export INNOVAE_GOOGLE_ACCOUNT='TU_GMAIL'
export INNOVAE_SERVICE_ACCOUNT='chatbot-innovae@ID_DE_TU_PROYECTO.iam.gserviceaccount.com'
export INNOVAE_APPS_SCRIPT_URL='https://script.google.com/macros/s/ID_REAL/exec'
bash desplegar-web.sh
```

El script configura Cloud Run en Madrid y conecta el secreto sin imprimir la clave.
También permite el origen de la demo del propio servicio, además de GitHub Pages.
No configura Meta. La cuenta que despliega necesita permisos para Cloud Build,
Cloud Run, Artifact Registry y gestionar el acceso al secreto y a la cuenta de servicio.

Después, revisar `/health` y probar una conversación con Claude y una solicitud
ficticia. El campo `ia: activa` de `/health` indica configuración presente; no
comprueba por sí solo la validez de la clave ni el saldo del proveedor.
Solo tras esa validación, copiar la URL HTTPS de Cloud Run a `api` en
`assets/chatbot-config.js` y publicar la web. Revisar también las referencias al
proveedor, alojamiento y conservación de datos en la política de privacidad.
Las sesiones están en memoria y pueden perderse al reiniciar la instancia.

## Estado sin cuentas

Se pueden comprobar los nombres, los avisos, la interfaz y el flujo simulado.
Quedan pendientes la creación de cuentas, el límite de gasto real, la clave,
la reserva completa con servicios reales y el despliegue. No hay un servicio
Claude publicado hasta completar esos pasos. WhatsApp se deja para otra fase.

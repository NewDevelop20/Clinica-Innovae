# Chatbot · Clínica Innovae

La fase actual es **solo web**. Consulta [la guía de puesta en marcha](PUESTA_EN_MARCHA.md): distingue lo preparado y probado sin credenciales de la activación real pendiente de las cuentas de Anthropic y Google Cloud. WhatsApp permanece desactivado.

Widget informativo para la web y backend con IA (Claude) preparado para web y WhatsApp.
La primera versión publicada funciona sin servicios externos. El backend puede resolver
consultas con IA y crear **solicitudes de cita** cuando se conecten Anthropic y un Web App
de Google Apps Script compatible. El Web App adaptado para Calendar sin hojas está en `reservas/Code.gs`; consulta `reservas/README.md`.

```
   Web (widget)  ─┐                       ┌─► Claude API (instrucciones + conocimiento)
                  ├─► Backend FastAPI ────┤
   WhatsApp ──────┘   (Cloud Run)         └─► Code.gs (Apps Script)
                                               ├─ ?disponibilidad=  → horas ocupadas
                                               └─ POST reserva      → evento 🟡 PENDIENTE + email
```

Un solo "cerebro" para los dos canales: mismas instrucciones, mismo conocimiento y misma agenda.
La clínica sigue confirmando o rechazando las citas desde el email, igual que con el formulario.

## Estructura

| Ruta | Qué es |
|---|---|
| `app/prompt.py` | Instrucciones del asistente (tono, límites médicos, flujo de reserva). |
| `conocimiento/*.md` | Lo que el bot sabe: clínica, 25 tratamientos + primera consulta + consulta general, productos. **Se edita aquí, sin tocar código.** |
| `app/herramientas.py` | Herramientas que usa Claude: consultar disponibilidad, crear solicitud, derivar a persona. |
| `app/agente.py` | Bucle de conversación con Claude (común a todos los canales) + modo simulado. |
| `app/whatsapp.py` | Webhook de Meta: verificación, firma, lectura de mensajes y envío de respuestas. |
| `app/main.py` | API: `/api/chat`, `/webhook/whatsapp`, `/health`, `/widget/…`, `/demo`. |
| `widget/innovae-chat.js` | Chat para la web, en un solo archivo (Shadow DOM: no choca con tus estilos). |
| `tests/` | Pruebas con Claude, Apps Script y Meta simulados (no hace falta ninguna clave). |

## Estado de la integración en esta web

La web y las 11 fichas cargan el widget desde `assets/chatbot/innovae-chat.js`.
Mientras `assets/chatbot-config.js` tenga `api: ''`, responde en el navegador con
27 opciones de tratamiento, las 11 fichas reales y preguntas frecuentes. Es una consulta
sin IA: reconoce temas y nombres, no entiende cualquier pregunta ni inventa datos.
No envía los mensajes al backend, a Anthropic, a Meta ni a una agenda; el historial
se guarda en sessionStorage de esta pestaña y se borra con «Reiniciar».
Las solicitudes de cita del chat están desactivadas y se ofrece contacto con la clínica.
El formulario está preparado para el Web App de `reservas/Code.gs`; se activa al configurar la URL real de despliegue.

Para actualizar los datos y el widget público después de editar sus fuentes:

```bash
node generar-productos.cjs
python chatbot/exportar_web.py
```

`chatbot/widget/innovae-chat.js` es la fuente; `assets/chatbot/` es su copia pública.
El exportador usa los tratamientos adjuntos y `productos/datos-productos.json`.
No publica los comentarios internos ni los datos provisionales del equipo.
Los nombres de tratamiento se han igualado a las opciones del formulario.

## Activar solo preguntas con IA (sin agenda ni WhatsApp)

GitHub Pages no ejecuta Python. Para conversaciones libres con Claude se necesita
un servicio HTTPS (por ejemplo Cloud Run) y una cuenta Anthropic con API key.
No hace falta configurar Meta ni Apps Script para esta primera fase.

Desde la carpeta `chatbot`, con el proyecto Google Cloud y la facturación ya habilitados,
y `anthropic-key` creado en Secret Manager:

```bash
gcloud run deploy chatbot-innovae --source . --region europe-southwest1 \
  --allow-unauthenticated --max-instances 1 --concurrency 8 --timeout 300 --memory 512Mi \
  --set-env-vars MODO_SIMULADO=0,ANTHROPIC_MODEL=claude-haiku-5-5,ORIGENES_PERMITIDOS=https://newdevelop20.github.io \
  --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest
```

La cuenta de servicio de Cloud Run necesita acceso al secreto. Consulta la URL que
produce el despliegue y comprueba `/health`. Guarda esa URL en `assets/chatbot-config.js`
(por ejemplo `api: 'https://chatbot-innovae-xxxx.run.app'`) y publica el cambio.
La configuración del navegador solo contiene una URL pública, nunca claves.
Prueba preguntas reales de horarios, precios, productos y tratamientos; las pruebas
simuladas no verifican la calidad ni la disponibilidad real de Claude.
Antes de activar IA, adapta la política de privacidad al proveedor y al uso de mensajes.

Las sesiones, límites y deduplicación viven en memoria: se pierden al reiniciar o
reemplazar la instancia. `--max-instances 1` reduce problemas de reparto, pero no
aporta persistencia. Para reservas en producción conviene usar almacenamiento
compartido, idempotencia de solicitudes y una cola de mensajes WhatsApp.

## Probar en local (sin API key)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest -q                                      # 50 pruebas

cp .env.example .env                                    # deja MODO_SIMULADO=1
uvicorn app.main:app --reload --port 8000
```

Abre http://localhost:8000/demo. En modo simulado el bot no usa IA, pero sí prueba todo el
circuito. Si pones tu `APPS_SCRIPT_URL` en `.env`, escribir `Limpieza Facial 2026-10-20`
consulta la **agenda real** a través del `Code.gs`.

Para activar la IA: rellena `ANTHROPIC_API_KEY` y pon `MODO_SIMULADO=0`.

## Verificar el widget en navegador

Desde la raíz del repositorio, después de instalar `chatbot/requirements-dev.txt`:

```bash
python -m playwright install chromium
python chatbot/tests/verificar_widget.py
```

Comprueba las 38 consultas del catálogo y preguntas frecuentes, límites médicos,
reinicio, historial, teclado, texto seguro y las 11 fichas a 1440 y 390 px.
Utiliza el puerto 8765. No llama a Anthropic, Meta ni al calendario.

## Añadirlo a otras webs (una línea)

Antes de `</body>` en `index.html`:

```html
<script src="https://TU-SERVICIO.run.app/widget/innovae-chat.js" defer></script>
```

Opciones: `data-posicion="izquierda"`, `data-margen-inferior="96"` (si choca con otro botón flotante).
Desde cualquier botón de la web se puede abrir el chat con un mensaje ya escrito:

```html
<button onclick="InnovaeChat.abrir('Quiero pedir cita para Radiofrecuencia')">Pregúntanos</button>
```

## Desplegar en Cloud Run

```bash
gcloud run deploy chatbot-innovae --source . --region europe-southwest1 \
  --allow-unauthenticated --max-instances 1 --concurrency 8 --timeout 300 --memory 512Mi \
  --set-env-vars MODO_SIMULADO=0,ANTHROPIC_MODEL=claude-haiku-5-5,APPS_SCRIPT_URL=https://script.google.com/macros/s/XXX/exec \
  --set-env-vars ORIGENES_PERMITIDOS=https://newdevelop20.github.io \
  --set-secrets ANTHROPIC_API_KEY=anthropic-key:latest,WHATSAPP_TOKEN=wa-token:latest,WHATSAPP_APP_SECRET=wa-secret:latest \
  --set-env-vars WHATSAPP_PHONE_NUMBER_ID=XXXX,WHATSAPP_VERIFY_TOKEN=tu-frase
```

- `europe-southwest1` es Madrid.
- `--max-instances 1`: limita instancias; las conversaciones en memoria se pierden al reiniciar. No garantiza persistencia durante despliegues.
- Las claves van en **Secret Manager**, nunca en el código ni en GitHub.
- Comprueba `https://TU-SERVICIO.run.app/health`. La prueba con cuentas reales sigue siendo necesaria.

## Conectar WhatsApp

1. En developers.facebook.com → tu app → WhatsApp → Configuración → Webhook:
   - URL: `https://TU-SERVICIO.run.app/webhook/whatsapp`
   - Token de verificación: el mismo valor que `WHATSAPP_VERIFY_TOKEN`.
2. Suscribe el campo **messages**.
3. `WHATSAPP_APP_SECRET` está en Configuración de la app → Básica. Con él se verifica que
   cada aviso viene de verdad de Meta.

⚠️ Un número conectado a la Cloud API no se puede usar a la vez en la app normal de
WhatsApp Business, salvo que Meta lo permita con su modo de "coexistencia". Conviene decidirlo
con la clínica antes de conectar el número principal (alternativa: un segundo número para el bot).

## Pendiente antes de producción

- [ ] Comprobar que los nombres de `conocimiento/tratamientos.md` (encabezados `###`) son
      idénticos a las opciones del desplegable del formulario. `Code.gs` los compara para no
      repetir el mismo tratamiento en la misma franja.
- [ ] Confirmar con la clínica: política de cancelación, aparcamiento, formas de pago
      (hay huecos marcados como `PENDIENTE` en `conocimiento/clinica.md`).
- [ ] Datos reales de Marta, Lucía y Andrea.
- [ ] Política de privacidad: añadir que el chat usa un proveedor de IA (Anthropic) para
      procesar los mensajes y gestionar la cita.
- [ ] Crear API key en console.anthropic.com con un **límite de gasto mensual**.

## Costes orientativos

Haiku es el modelo más económico de Claude y las instrucciones y el conocimiento se cachean
para abaratar cada mensaje (precios actuales en docs.claude.com). El límite de gasto mensual
de la Console evita sorpresas. Cloud Run entra en la capa gratuita con este volumen.


## Profesional en las reservas

El backend consulta el catálogo del Web App y usa el ID seleccionado tanto en
la disponibilidad como en el envío. La herramienta `consultar_profesionales`
devuelve IDs, nombres y tratamientos; sin preferencia se usa `cualquiera`.
El mismo calendario admite una cita por profesional y hasta dos a la vez.
Para que esta función exista, actualiza la implementación Google según
`reservas/README.md`. Marta y Lucía están configuradas para pruebas; antes de
producción hay que confirmar sus tratamientos reales.

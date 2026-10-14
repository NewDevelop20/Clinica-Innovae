# Reservas con Google Calendar, sin hoja de cálculo

El formulario y el chatbot comparten este Web App de Google Apps Script.
Los datos del cliente quedan en Calendar. Las propiedades del script guardan
solo IDs, tokens, estado y datos de reintento (sin nombre, correo ni teléfono).
Los índices caducan a los 180 días; el historial del calendario permanece.

Los avisos de pruebas van a **vicentenavasmoya@gmail.com**. La cuenta que despliega
es la que crea los eventos y envía los correos. No se necesita Google Sheets.

## Despliegue inicial desde tu cuenta

1. Abre <https://script.google.com/home/start> con tu cuenta de Google y crea un proyecto
   llamado «Reservas Innovae».
2. Sustituye el contenido de `Code.gs` por el archivo de esta carpeta.
3. En Configuración del proyecto, activa «Mostrar el archivo de manifiesto appsscript.json
   en el editor». Sustituye ese manifiesto por el incluido aquí. Usa zona Europe/Madrid.
4. Pulsa **Implementar → Nueva implementación → Aplicación web**.
   Elige **Ejecutar como: yo** y **Quién tiene acceso: cualquier usuario** (sin iniciar sesión).
   Autoriza Calendar y el envío de correo. No se solicitan permisos para hojas de cálculo.
5. Copia la URL terminada en `/exec`. No uses `/dev`, un ID de proyecto ni la URL del editor.
6. Ejecuta `prepararPruebas` desde el selector de funciones del editor. Crea un calendario
   aparte «Innovae — pruebas de reservas» y guarda su ID; no usa tu agenda personal.
7. Ejecuta `probarReserva`. Crea una solicitud ficticia para el siguiente día abierto y envía
   los avisos solo a tu correo personal. Comprueba el evento amarillo y el correo con enlaces.
8. Prueba los enlaces: confirmar cambia el evento a verde; rechazar lo elimina. El estado
   se conserva en Apps Script para evitar gestionar dos veces el mismo enlace.

El código debe desplegarse como aplicación web pública, pero los enlaces de gestión
requieren un token aleatorio que solo aparece en el calendario y en el correo de avisos.
No compartas esos enlaces. El filtro de spam no sustituye una protección contra abuso:
las cuotas de Apps Script y Mail dependen de la cuenta.

## Conectar la URL al sitio y al chatbot

Cuando exista la URL real, ponla en `assets/reservas-config.js`:

```js
window.INNOVAE_RESERVAS_CONFIG = {
  endpoint: 'https://script.google.com/macros/s/ID_REAL/exec'
};
```

Es una dirección pública, no una clave. Mientras está vacía, el formulario explica que
no está conectado y no muestra una confirmación falsa. El sitio no puede crear por sí
solo el proyecto Google ni autorizar la cuenta.

Para el chatbot, usa la misma URL como variable del servidor:

```text
APPS_SCRIPT_URL=https://script.google.com/macros/s/ID_REAL/exec
```

El backend Python aún necesita su propio alojamiento y conexión con Anthropic para
conversaciones con IA. El chat informativo publicado sin IA no crea reservas.

## Pruebas antes de aceptar clientes reales

- Enviar el formulario con datos ficticios, usando tu correo tanto para avisos como
  para el campo Email del cliente. Comprobar solicitud, evento y ambos correos.
- Elegir una franja ocupada y comprobar que se rechaza sin mostrar éxito.
- Confirmar y rechazar una solicitud distinta en cada prueba y revisar el correo al cliente.
- Reintentar un envío sin modificar los campos: debe volver a mostrar el mismo código.
- Comprobar horas de lunes a viernes y sábado; domingos no se ofrecen.

Las pruebas locales con servicios simulados no demuestran permisos, cuotas, recepción
real de correos ni el funcionamiento del entorno de Google. Estos pasos reales son
necesarios antes de considerar las reservas operativas.

## Cambiar de pruebas a clínica

En Configuración del proyecto → Propiedades del script configura:

- `CALENDAR_ID`: el calendario real (la cuenta que despliega debe tener permiso de escritura).
- `EMAIL_AVISOS`: correo real de la clínica cuando terminen las pruebas.
- `WEB_APP_URL`: opcional, la URL `/exec` si Google no la detecta correctamente.

Revisa también `MAX_SIMULTANEAS` (actualmente 2), `DURACION_MIN` (60) y el horario.
Los eventos manuales que se solapen bloquean la franja; los eventos de reservas aplican
la capacidad y no permiten dos citas del mismo tratamiento a la vez.
Al modificar el código, edita la implementación y selecciona una **nueva versión**,
conservando la misma URL. Las propiedades no requieren copiar claves al sitio.
Los índices de gestión residen en propiedades de Apps Script y están sujetos a su cuota;
para alto volumen habrá que sustituir ese índice por almacenamiento apropiado.

## Transporte y pruebas automáticas

El backend Python usa JSON para consultar disponibilidad y crear solicitudes. El formulario
consulta disponibilidad por JSONP y envía datos por POST a un iframe de Google; acepta
la respuesta solo desde Google y con el ID aleatorio esperado. Así se puede comprobar
el resultado sin recurrir a respuestas opacas de `fetch(..., mode: 'no-cors')`.
No se envían nombres, teléfonos ni correos por parámetros GET.

```bash
node --test reservas/tests/apps-script.test.cjs
python reservas/tests/verificar_formulario.py
```

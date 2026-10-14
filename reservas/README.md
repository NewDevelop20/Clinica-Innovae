# Reservas con Google Calendar, sin hoja de cálculo

El formulario y el backend del chatbot usan la misma URL de Google Apps Script.
La URL está configurada en `assets/reservas-config.js`, `reservas/Code.gs` y
`chatbot/.env.example`. El despliegue sigue apuntando al calendario de pruebas y
los avisos van al correo personal; no se ha cambiado al calendario de la clínica.
El formulario muestra un aviso de pruebas (`modoPruebas: true`) para evitar que
los visitantes confundan una prueba con una solicitud de cita real.
La conexión real se verificó el 14/10/2026 desde el formulario: solicitud ficticia
1C0C8B2A para Limpieza Facial, 19/10/2026 a las 10:00. Google devolvió el código y
aceptó el envío del correo. Falta que el usuario compruebe su recepción y pruebe
los enlaces de gestión. La prueba debe rechazarse al terminar para liberar el hueco.
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
6. Si el editor devuelve una URL `/dev`, configura `WEB_APP_URL` con la URL `/exec`
   en las propiedades del script, o en la línea `WEB_APP_URL` de `CONFIG`.
   El valor por defecto de este repositorio ya usa el despliegue actual. No conviertas
   una URL `/dev` a `/exec` cambiando su sufijo: los identificadores pueden ser distintos.
   Ejecuta `prepararPruebas` desde el selector de funciones del editor. Crea un calendario
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

La URL real ya está en `assets/reservas-config.js`. Si se cambia el despliegue, actualízala:

```js
window.INNOVAE_RESERVAS_CONFIG = {
  endpoint: 'https://script.google.com/macros/s/ID_REAL/exec'
};
```

Es una dirección pública, no una clave. Si se deja vacía, el formulario explica que
no está conectado y no muestra una confirmación falsa. El sitio no puede crear por sí
solo el proyecto Google ni autorizar la cuenta.

Para el chatbot, usa la misma URL como variable del servidor:

```text
APPS_SCRIPT_URL=https://script.google.com/macros/s/ID_REAL/exec
```

La URL también está preparada en `chatbot/.env.example`. El backend Python aún necesita su propio alojamiento y conexión con Anthropic para
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

Cuando se hayan comprobado el calendario real, el destinatario y los enlaces de gestión,
configura `modoPruebas: false` en `assets/reservas-config.js` para admitir solicitudes reales.
Revisa también `MAX_SIMULTANEAS` (actualmente 2), `DURACION_MIN` (60) y el horario.
Los eventos manuales que se solapen bloquean la franja; los eventos de reservas aplican
la capacidad global de dos y una cita por profesional; se permiten dos citas del
mismo tratamiento cuando las atienden profesionales distintos.
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

## Selección de profesional (actualización)

Se han añadido Marta Jiménez y Lucía Serrano para las pruebas, con todos los
tratamientos habilitados por petición del usuario. Es solo una configuración de
prueba: no define sus atribuciones médicas reales. La web obtiene el equipo del
script para evitar mantener dos listas distintas.

Para activar la selección en el despliegue que ya existe:

1. Sustituye el contenido de Código.gs en el editor por `reservas/Code.gs` de este repositorio.
   La URL /exec ya está escrita como valor por defecto. Guarda.
2. Implementar → Gestionar implementaciones → selecciona la aplicación web → lápiz Editar.
3. En Versión, elige **Nueva versión** y pulsa Implementar. Conserva Ejecutar como yo
   y acceso Cualquier usuario. La URL sigue siendo la misma.
4. Recarga la web. Debe aparecer Profesional con Marta, Lucía y «Cualquier profesional disponible».

No vuelvas a ejecutar prepararPruebas ni borres las propiedades: el ID del calendario
y los enlaces de las solicitudes existentes se conservan. La web mantiene el
formulario anterior hasta que Google publique la nueva versión con el catálogo.
Los clientes antiguos que no envían profesional reciben asignación automática
cuando se atienden con la versión nueva.

En las solicitudes nuevas, el nombre del profesional aparece en el evento, el
aviso a la clínica, los correos al cliente, la página de gestión y el resumen web.
Cambiar el profesional vuelve a consultar las horas. La asignación sin preferencia
se hace dentro del mismo bloqueo que comprueba disponibilidad y crea el evento.

Antes de producción, edita `PROFESIONALES_PRUEBAS` en Code.gs o usa la propiedad
`PROFESIONALES` con una lista JSON de objetos `id`, `nombre` y `tratamientos`.
Los nombres de tratamientos deben coincidir con el formulario. No cambies los IDs
de personas que ya tengan citas: sus reservas se identifican por ese ID.
Los eventos antiguos sin profesional bloquean su franja por precaución hasta que
se rechacen/eliminen o se revisen; no se asigna una persona ficticia a reservas pasadas.

El backend del chatbot puede consultar el catálogo con `consultar_profesionales`,
y envía el mismo ID al consultar disponibilidad y crear la solicitud. La versión
informativa sin IA continúa sin gestionar citas.

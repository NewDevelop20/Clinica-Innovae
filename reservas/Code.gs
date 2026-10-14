/**
 * ============================================================
 *  CLÍNICA INNOVAE · Central de reservas web → Google Calendar
 * ============================================================
 *  Flujo:
 *   1. La web envía la reserva (POST) a este Web App.
 *   2. Se crea un evento AMARILLO "🟡 PENDIENTE" en el calendario de la clínica,
 *      se guardan los códigos de gestión en Apps Script y se envía un email a la clínica
 *      con dos botones: CONFIRMAR / RECHAZAR (los enlaces también van en la
 *      descripción del evento, así se puede gestionar desde el propio calendario).
 *   3. Al pulsar un botón se abre una página de confirmación (se pide un clic
 *      más para que los antivirus del correo no confirmen solos al escanear el enlace).
 *   4. CONFIRMAR → evento pasa a VERDE "✅" + email de confirmación al cliente.
 *      RECHAZAR  → se borra el evento + email al cliente invitándole a elegir otra hora.
 *
 *  IMPORTANTE: este script debe crearse y desplegarse con la CUENTA DE GOOGLE
 *  DE LA CLÍNICA (es la que tiene el calendario y la que envía los correos).
 * ============================================================
 */

const CONFIG = {
  // 'primary' = calendario principal de la cuenta que despliega el script.
  // Si preferís un calendario aparte ("Reservas web"), pega aquí su ID
  // (Calendar → Configuración del calendario → Integrar el calendario → ID).
  CALENDAR_ID: PropertiesService.getScriptProperties().getProperty('CALENDAR_ID') || 'primary',

  // Correo que recibe los avisos. Vacío = la propia cuenta de la clínica.
  EMAIL_AVISOS: PropertiesService.getScriptProperties().getProperty('EMAIL_AVISOS') || 'vicentenavasmoya@gmail.com',

  // URL del Web App (/exec). Vacío = se detecta sola. Si los enlaces de los
  // emails salen con /dev, pega aquí la URL /exec del despliegue.
  WEB_APP_URL: PropertiesService.getScriptProperties().getProperty('WEB_APP_URL') || 'https://script.google.com/macros/s/AKfycbwM4CVNFtDSfYyQLB9J23iXylOfaPcrx1ck9ss0MKPWGGtldsiLxaAxL5w5VUeYz4ef/exec',

  NOMBRE_CLINICA: 'Clínica Innovae',
  TELEFONO: '661 73 48 70',
  WHATSAPP: 'https://wa.me/34661734870',
  DIRECCION: 'Av. Ramón y Cajal 10, 23400 Úbeda (Jaén)',
  WEB: 'https://newdevelop20.github.io/Clinica-Innovae/#reservas',

  DURACION_MIN: 60,          // duración por defecto de cada cita en el calendario
  AVISO_MIN_ANTES: 60,       // recordatorio emergente en el calendario X min antes de la cita

  // Capacidad de la clínica: nº de profesionales que pueden atender A LA VEZ.
  // Regla: en una misma franja caben como máximo MAX_SIMULTANEAS citas,
  // Cada profesional atiende una cita por franja, incluso con tratamientos distintos.
  MAX_SIMULTANEAS: 2,

  // Nombre de cada campo tal y como lo envía el formulario de la web (atributo name).
  // Ajusta SOLO la parte derecha si tus nombres son distintos.
  CAMPOS: {
    nombre: 'nombre',
    telefono: 'telefono',
    email: 'email',
    tratamiento: 'tratamiento',
    profesional: 'profesional',
    fecha: 'fecha',          // admite "2026-10-15" o "15/10/2026"
    hora: 'hora',            // "10:30"
    primeraVisita: 'primeraVisita',
    comentarios: 'comentarios',
    honeypot: 'website'      // campo trampa anti-spam (debe llegar vacío)
  }
};


const TRATAMIENTOS_VALIDOS = ["Primera consulta / valoración", "Eliminación de Arrugas", "Rellenos con Ácido Hialurónico", "Hilos Tensores", "Mesoterapia", "Endolifting con Fibra Óptica", "Eliminación de Manchas y Lesiones (Blumed)", "Eliminación de Arañas Vasculares", "Limpieza Facial", "Peeling Mecánico", "Hidratación", "Oxigenación", "Vitamina C", "Reafirmante", "Kinesiolifting", "Radiofrecuencia", "Fotorejuvenecimiento", "Ultrasonix", "Dermapen", "Depilación SHR", "Depilación IPL", "Maderoterapia", "Presoterapia", "Drenajes Linfáticos", "Hondas Magnéticas", "Cera Facial y Corporal", "Otro / Consulta general"];

// Miembros elegidos para las pruebas; no define sus atribuciones clínicas reales.
const PROFESIONALES_PRUEBAS = [
  {id: 'marta-jimenez', nombre: 'Marta Jiménez', tratamientos: TRATAMIENTOS_VALIDOS},
  {id: 'lucia-serrano', nombre: 'Lucía Serrano', tratamientos: TRATAMIENTOS_VALIDOS}
];
function profesionales_() {
  const raw = PropertiesService.getScriptProperties().getProperty('PROFESIONALES');
  const lista = raw ? JSON.parse(raw) : PROFESIONALES_PRUEBAS;
  if (!Array.isArray(lista) || !lista.length || lista.some(p => !/^[a-z0-9-]{3,60}$/.test(p.id) || typeof p.nombre !== 'string' || !p.nombre.trim() || p.nombre.length > 100 || !Array.isArray(p.tratamientos))) throw new Error('Configuración de profesionales no válida.');
  if (new Set(lista.map(p => p.id)).size !== lista.length) throw new Error('ID de profesional repetido.');
  return lista;
}
function candidatos_(tratamiento, profesional) {
  const elegidos = profesionales_().filter(p => !profesional || profesional === 'cualquiera' || p.id === profesional);
  return elegidos.filter(p => p.tratamientos.some(t => normalizar_(t) === normalizar_(tratamiento)));
}

const HORARIO_RESERVAS = {0: [], 1: [['10:00','13:30'],['16:30','20:30']], 2: [['10:00','13:30'],['16:30','20:30']], 3: [['10:00','13:30'],['16:30','20:30']], 4: [['10:00','13:30'],['16:30','20:30']], 5: [['10:00','13:30'],['16:30','20:30']], 6: [['10:30','13:00']]};
function minutos_(hora) { const p = hora.split(':'); return +p[0] * 60 + +p[1]; }
function validarReserva_(d, inicio) {
  if (d.nombre.length < 2 || !/^\+?\d{9,15}$/.test(d.telefono)) return 'Nombre o teléfono no válidos.';
  if (!TRATAMIENTOS_VALIDOS.some(t => normalizar_(t) === normalizar_(d.tratamiento))) return 'Tratamiento no válido.';
  if (!candidatos_(d.tratamiento, d.profesional).length) return 'El profesional seleccionado no atiende ese tratamiento.';
  if (inicio.getTime() < Date.now() + 60 * 60000) return 'Elija una fecha y hora con al menos una hora de antelación.';
  const limite = new Date(Date.now() + 90 * 86400000);
  if (Utilities.formatDate(inicio, zona_(), 'yyyy-MM-dd') > Utilities.formatDate(limite, zona_(), 'yyyy-MM-dd')) return 'Solo se admiten citas con hasta 90 días de antelación.';
  const dia = +Utilities.formatDate(inicio, zona_(), 'u') % 7;
  const minutos = minutos_(d.hora);
  if (minutos % 30 || !HORARIO_RESERVAS[dia].some(p => minutos >= minutos_(p[0]) && minutos + CONFIG.DURACION_MIN <= minutos_(p[1]))) return 'Hora fuera del horario de reservas.';
  return '';
}

// Formulario web: respuesta verificable por postMessage, sin respuestas opacas de no-cors.
function respuestaReserva_(datos, e) {
  const p = (e && e.parameter) || {};
  if (p.transporte !== 'iframe') return json_(datos);
  if (!/^[A-Za-z0-9_-]{16,80}$/.test(p.requestId || '')) return HtmlService.createHtmlOutput('Solicitud no válida.');
  const mensaje = JSON.stringify({tipo: 'innovae-reserva', requestId: p.requestId, resultado: datos}).replace(/</g, '\\u003c');
  return HtmlService.createHtmlOutput('<!doctype html><script>window.top.postMessage(' + mensaje + ', "https://newdevelop20.github.io");<\/script>')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
function respuestaDisponibilidad_(datos, callback) {
  if (!callback) return json_(datos);
  if (!/^innovaeAvailability_[A-Za-z0-9_]{8,80}$/.test(callback)) return json_({ok: false, error: 'Callback no válido.'});
  return ContentService.createTextOutput(callback + '(' + JSON.stringify(datos).replace(/</g, '\\u003c') + ');').setMimeType(ContentService.MimeType.JAVASCRIPT);
}

const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
  'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];


/* ============================================================
 *  1. RECEPCIÓN DE RESERVAS (la web hace POST aquí)
 * ============================================================ */
function doPost(e) {
  try {
    const d = leerDatos_(e);

    // Anti-spam: nunca registrar una solicitud con el campo trampa relleno.
    if (d.honeypot) return respuestaReserva_({ ok: false, error: 'Solicitud no válida.' }, e);

    const faltan = ['nombre', 'telefono', 'tratamiento', 'fecha', 'hora'].filter(k => !d[k]);
    if (faltan.length) return respuestaReserva_({ ok: false, error: 'Faltan campos: ' + faltan.join(', ') }, e);

    const inicio = parsearFechaHora_(d.fecha, d.hora);
    if (!inicio) return respuestaReserva_({ ok: false, error: 'Fecha u hora no válidas' }, e);
    const error = validarReserva_(d, inicio);
    if (error) return respuestaReserva_({ ok: false, error: error }, e);
    const fin = new Date(inicio.getTime() + CONFIG.DURACION_MIN * 60000);

    const res = crearReserva_(d, inicio, fin);
    return respuestaReserva_(res, e);

  } catch (err) {
    console.error(err);
    return respuestaReserva_({ ok: false, error: 'No se pudo registrar la solicitud. Contacte con la clínica.' }, e);
  }
}

function crearReserva_(d, inicio, fin) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    purgarIndices_();
    if (d.requestId) {
      const previa = buscarRequest_(d.requestId);
      if (previa) return {ok: true, id: previa.id, estado: previa.estado, aviso_enviado: previa.aviso, profesional: previa.profesionalNombre || ''};
    }
    const cal = calendario_();

    // Comprobación de disponibilidad (dentro del bloqueo: dos reservas
    // simultáneas no pueden colarse a la vez en el último hueco).
    const disp = comprobarDisponibilidad_(cal, d.tratamiento, inicio, fin, null, d.profesional);
    if (!disp.ok) return disp;
    d.profesionalId = disp.profesional.id;
    d.profesionalNombre = disp.profesional.nombre;

    let id = Utilities.getUuid().slice(0, 8).toUpperCase();
    while (PropertiesService.getScriptProperties().getProperty('RESERVA_' + id)) id = Utilities.getUuid().slice(0, 8).toUpperCase();
    const token = Utilities.getUuid().replace(/-/g, '');

    const titulo = '🟡 PENDIENTE · ' + d.nombre + ' · ' + d.tratamiento + ' · ' + d.profesionalNombre;
    const urlConfirmar = urlAccion_(id, token, 'confirmar');
    const urlRechazar = urlAccion_(id, token, 'rechazar');

    const descripcion = [
      'Reserva web #' + id,
      '',
      '👤 ' + d.nombre,
      '📞 ' + d.telefono,
      d.email ? '✉️ ' + d.email : '',
      '💆 ' + d.tratamiento,
      '👩‍⚕️ Profesional: ' + d.profesionalNombre,
      '🆕 Primera visita: ' + (d.primeraVisita ? 'Sí' : 'No'),
      d.comentarios ? '📝 ' + d.comentarios : '',
      '',
      '✅ CONFIRMAR: ' + urlConfirmar,
      '❌ RECHAZAR: ' + urlRechazar
    ].filter(l => l !== '').join('\n');

    const ev = cal.createEvent(titulo, inicio, fin, { description: descripcion, location: CONFIG.DIRECCION });
    ev.setTag('reservaId', id);
    ev.setTag('tratamiento', normalizar_(d.tratamiento));
    ev.setColor(CalendarApp.EventColor.YELLOW);
    ev.removeAllReminders();
    ev.addPopupReminder(CONFIG.AVISO_MIN_ANTES);

    let registro;
    try {
      ev.setTag('profesional', d.profesionalId);
      ev.setTag('profesionalNombre', d.profesionalNombre);
      ev.setTag('clienteNombre', d.nombre);
      ev.setTag('clienteEmail', d.email);
      ev.setTag('clienteTelefono', d.telefono);
      ev.setTag('tratamientoNombre', d.tratamiento);
      registro = {id: id, token: token, eventId: ev.getId(), estado: 'PENDIENTE', creada: Date.now(), requestId: d.requestId, aviso: false, profesionalNombre: d.profesionalNombre};
      guardarIndice_(registro);
    } catch (err) {
      ev.deleteEvent();
      throw err;
    }
    let aviso = true;
    try { avisarClinica_(id, d, inicio, urlConfirmar, urlRechazar); }
    catch (err) { aviso = false; console.error('Aviso a clínica fallido'); }
    registro.aviso = aviso;
    guardarIndice_(registro);
    if (d.email) emailRecibida_(d, inicio);
    return { ok: true, id: id, estado: 'PENDIENTE', aviso_enviado: aviso, profesional: d.profesionalNombre };
  } finally {
    lock.releaseLock();
  }
}


/** Una agenda compartida: cada profesional puede tener una cita por franja.
 * Se permiten dos citas del mismo tratamiento si las atienden profesionales distintos.
 * Los eventos antiguos sin profesional y los eventos manuales bloquean la franja
 * hasta asignarlos o eliminarlos: no se inventa quién los atiende.
 */
function comprobarDisponibilidad_(cal, tratamiento, inicio, fin, eventosDia, profesional) {
  const solapadas = (eventosDia || cal.getEvents(inicio, fin))
    .filter(ev => ev.getStartTime() < fin && ev.getEndTime() > inicio);
  const candidatos = candidatos_(tratamiento, profesional);
  if (!candidatos.length) return {ok: false, motivo: 'profesional_no_valido', error: 'El profesional no atiende ese tratamiento.'};
  if (solapadas.some(ev => !ev.getTag('profesional'))) return {ok: false, motivo: 'ocupado', error: 'Hay un evento sin profesional asignado en esa franja. Elija otra hora o contacte con la clínica.'};
  // Capacidad máxima concurrente: dos eventos consecutivos no deben contarse
  // como simultáneos solo porque ambos toquen la franja solicitada.
  const puntos = [inicio.getTime()].concat(solapadas.map(ev => ev.getStartTime().getTime()).filter(t => t > inicio && t < fin));
  if (puntos.some(t => solapadas.filter(ev => ev.getStartTime().getTime() <= t && ev.getEndTime().getTime() > t).length >= CONFIG.MAX_SIMULTANEAS)) {
    return {ok: false, motivo: 'completo', error: 'Esa hora ya está completa. Por favor, elija otra hora.'};
  }
  const libre = candidatos.find(p => !solapadas.some(ev => ev.getTag('profesional') === p.id));
  if (!libre) return {ok: false, motivo: 'profesional_ocupado', error: 'El profesional seleccionado no está libre a esa hora. Elija otro profesional u otra hora.'};
  return {ok: true, profesional: libre};
}

function tratamientoDeEvento_(ev) {
  const tag = ev.getTag('tratamiento');
  if (tag) return tag;
  const partes = ev.getTitle().split(' · ');           // "… · Nombre · Tratamiento"
  return normalizar_(partes[partes.length - 1]);
}

/** Minúsculas, sin tildes ni espacios extra, para comparar nombres de tratamiento. */
function normalizar_(s) {
  return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, ' ').trim();
}

/**
 * Consulta para la web: GET ?disponibilidad=2026-10-15&tratamiento=Limpieza facial
 * Devuelve las horas (cada 15 min, de 08:00 a 21:00) en las que ese tratamiento
 * NO se puede reservar, para desactivarlas en el selector de hora.
 */
function horasBloqueadas_(fecha, tratamiento, profesional) {
  const ini = parsearFechaHora_(fecha, '00:00');
  if (!ini) return { ok: false, error: 'Fecha no válida' };
  if (!candidatos_(tratamiento, profesional).length) return {ok: false, error: 'Profesional o tratamiento no válido.'};
  const cal = calendario_();
  const finDia = new Date(ini.getTime() + 24 * 3600000);
  const eventos = cal.getEvents(ini, finDia);
  const bloqueadas = [];
  for (let min = 8 * 60; min <= 21 * 60; min += 15) {
    const hora = pad_(Math.floor(min / 60)) + ':' + pad_(min % 60);
    const i = parsearFechaHora_(fecha, hora);
    const f = new Date(i.getTime() + CONFIG.DURACION_MIN * 60000);
    if (!comprobarDisponibilidad_(cal, tratamiento, i, f, eventos, profesional).ok) bloqueadas.push(hora);
  }
  return { ok: true, fecha: fecha, tratamiento: tratamiento, profesional: profesional || 'cualquiera', bloqueadas: bloqueadas };
}


/* ============================================================
 *  2. PÁGINA DE CONFIRMAR / RECHAZAR (enlaces del email y del calendario)
 *     + consulta de disponibilidad para la web
 * ============================================================ */
function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.catalogo === 'profesionales') {
    try { return respuestaDisponibilidad_({ok: true, version: 2, profesionales: profesionales_()}, p.callback); }
    catch (err) { return respuestaDisponibilidad_({ok: false, error: 'No se pudo cargar el equipo.'}, p.callback); }
  }
  if (p.disponibilidad) {
    try { return respuestaDisponibilidad_(horasBloqueadas_(p.disponibilidad, p.tratamiento || '', p.profesional || ''), p.callback); }
    catch (err) { return respuestaDisponibilidad_({ ok: false, error: 'No se pudo consultar la agenda.' }, p.callback); }
  }
  if (!p.id || !p.t) {
    return HtmlService.createHtmlOutput('<p style="font-family:sans-serif">Central de reservas activa.</p>')
      .setTitle(CONFIG.NOMBRE_CLINICA);
  }

  const r = buscarReserva_(p.id);
  const t = HtmlService.createTemplate(PAGINA_GESTION);
  t.clinica = CONFIG.NOMBRE_CLINICA;
  t.id = p.id;
  t.token = p.t;
  t.accion = p.accion === 'rechazar' ? 'rechazar' : 'confirmar';

  if (!r || r.registro.token !== p.t) {
    t.estado = 'ERROR'; t.resumen = 'Enlace no válido o reserva inexistente.';
  } else {
    t.estado = r.registro.estado;
    const d = r.datos;
    t.resumen = d ? d.nombre + ' · ' + d.tratamiento + ' · ' + d.fecha + ' a las ' + d.hora + ' · Profesional: ' + (d.profesionalNombre || 'Sin asignar') + ' · Tel. ' + d.telefono : 'Solicitud ' + String(t.estado).toLowerCase() + '.';
  }

  return t.evaluate()
    .setTitle('Gestionar reserva · ' + CONFIG.NOMBRE_CLINICA)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

/** Llamada desde el botón de la página (google.script.run). */
function procesarAccion(id, token, accion, mensaje) {
  const lock = LockService.getScriptLock();
  lock.waitLock(15000);
  try {
    const r = buscarReserva_(id);
    if (!r || r.registro.token !== token) return {ok: false, texto: 'Enlace no válido.'};
    if (r.registro.estado !== 'PENDIENTE') return {ok: false, texto: 'Esta solicitud ya está ' + r.registro.estado.toLowerCase() + '.'};
    const ev = r.evento, d = r.datos;
    if (!ev || !d) return {ok: false, texto: 'El evento ya no existe. Revise el calendario antes de gestionar la solicitud.'};
    const inicio = ev.getStartTime();
    mensaje = String(mensaje || '').trim().slice(0, 500);
    if (accion === 'confirmar') {
      ev.setTitle('✅ ' + d.nombre + ' · ' + d.tratamiento + (d.profesionalNombre ? ' · ' + d.profesionalNombre : ''));
      ev.setColor(CalendarApp.EventColor.GREEN);
      ev.setDescription(ev.getDescription().replace(/\n*✅ CONFIRMAR:[\s\S]*$/, '') + '\n\nEstado: CONFIRMADA');
      r.registro.estado = 'CONFIRMADA';
      guardarIndice_(r.registro);
      if (d.email) emailConfirmada_(d, inicio, mensaje);
      return {ok: true, texto: 'Cita confirmada.' + (d.email ? ' Se ha intentado enviar el aviso al cliente.' : ' Avísele por teléfono o WhatsApp.')};
    }
    if (accion === 'rechazar') {
      ev.deleteEvent();
      r.registro.estado = 'RECHAZADA';
      guardarIndice_(r.registro);
      if (d.email) emailRechazada_(d, inicio, mensaje);
      return {ok: true, texto: 'Solicitud rechazada y evento eliminado.' + (d.email ? ' Se ha intentado enviar el aviso al cliente.' : ' Avísele por teléfono o WhatsApp.')};
    }
    return {ok: false, texto: 'Acción no reconocida.'};
  } finally { lock.releaseLock(); }
}

const PAGINA_GESTION = `<!DOCTYPE html>
<html><head><base target="_top">
<style>
  body{font-family:Montserrat,Arial,sans-serif;background:#f7f2ea;color:#2b2622;margin:0;padding:24px}
  .card{max-width:480px;margin:40px auto;background:#fff;border-radius:14px;padding:28px;box-shadow:0 6px 24px rgba(0,0,0,.08)}
  h1{font-family:'Cormorant Garamond',Georgia,serif;font-weight:600;color:#a8874a;margin:0 0 6px}
  .res{background:#faf6ef;border-left:3px solid #c2a165;padding:12px 14px;margin:16px 0;line-height:1.5}
  textarea{width:100%;box-sizing:border-box;border:1px solid #ddd;border-radius:8px;padding:10px;font:inherit;min-height:80px}
  button{width:100%;padding:14px;border:0;border-radius:10px;font:600 15px Montserrat,Arial;color:#fff;cursor:pointer;margin-top:14px}
  .confirmar{background:#3c8d5a}.rechazar{background:#b5473f}
  .msg{margin-top:16px;font-weight:600}
</style></head>
<body><div class="card">
  <h1><?= clinica ?></h1>
  <div>Reserva #<?= id ?></div>
  <div class="res"><?= resumen ?></div>
  <? if (estado === 'PENDIENTE') { ?>
    <label>Mensaje opcional para el cliente</label>
    <textarea id="m" placeholder="<?= accion === 'rechazar' ? 'Ej.: Esa hora no está disponible, ¿le viene bien a las 12:00?' : 'Ej.: Recuerde venir sin maquillaje.' ?>"></textarea>
    <button id="b" class="<?= accion ?>" onclick="enviar()"><?= accion === 'rechazar' ? '❌ Rechazar reserva' : '✅ Confirmar cita' ?></button>
    <div class="msg" id="out"></div>
    <script>
      function enviar(){
        var b=document.getElementById('b'); b.disabled=true; b.textContent='Procesando…';
        google.script.run
          .withSuccessHandler(function(r){ document.getElementById('out').textContent=r.texto; b.style.display='none'; })
          .withFailureHandler(function(e){ document.getElementById('out').textContent='Error: '+e.message; b.disabled=false; })
          .procesarAccion(<?!= JSON.stringify(id) ?>, <?!= JSON.stringify(token) ?>, <?!= JSON.stringify(accion) ?>, document.getElementById('m').value);
      }
    </script>
  <? } else if (estado === 'ERROR') { ?>
    <div class="msg">⚠️ Enlace no válido.</div>
  <? } else { ?>
    <div class="msg">Esta reserva ya está <?= String(estado).toLowerCase() ?>.</div>
  <? } ?>
</div></body></html>`;


/* ============================================================
 *  3. EMAILS
 * ============================================================ */
function avisarClinica_(id, d, inicio, urlOk, urlKo) {
  const destino = CONFIG.EMAIL_AVISOS || Session.getEffectiveUser().getEmail();
  const cuando = fechaLarga_(inicio);
  const html = plantilla_(
    'Nueva reserva web',
    '<table style="font-size:15px;line-height:1.7">' +
    fila_('Cliente', d.nombre) + fila_('Teléfono', d.telefono) + fila_('Email', d.email || '—') +
    fila_('Tratamiento', d.tratamiento) + fila_('Profesional', d.profesionalNombre || 'Sin asignar') + fila_('Cuándo', cuando) +
    fila_('Primera visita', d.primeraVisita ? 'Sí' : 'No') + fila_('Comentarios', d.comentarios || '—') +
    '</table>' +
    '<p style="margin-top:24px">' +
    boton_(urlOk, '✅ Confirmar', '#3c8d5a') + '&nbsp;&nbsp;' + boton_(urlKo, '❌ Rechazar', '#b5473f') +
    '</p><p style="color:#888;font-size:12px">La cita ya aparece en amarillo en el calendario.</p>'
  );
  MailApp.sendEmail({
    to: destino,
    subject: '🟡 Nueva reserva #' + id + ' · ' + d.nombre + ' · ' + d.profesionalNombre + ' · ' + cuando,
    htmlBody: html,
    replyTo: d.email || undefined,
    name: CONFIG.NOMBRE_CLINICA + ' · Reservas web'
  });
}

function emailRecibida_(d, inicio) {
  enviarCliente_(d.email, 'Hemos recibido su solicitud de cita',
    '<p>Hola ' + esc_(d.nombre) + ',</p>' +
    '<p>Hemos recibido su solicitud para <b>' + esc_(d.tratamiento) + '</b> el <b>' + fechaLarga_(inicio) + '</b>.</p>' +
    '<p>Profesional: <b>' + esc_(d.profesionalNombre || 'Sin asignar') + '</b>.</p>' +
    '<p>En breve le confirmaremos la cita por email. Si lo necesita, puede llamarnos al ' + CONFIG.TELEFONO + '.</p>');
}

function emailConfirmada_(d, inicio, mensaje) {
  enviarCliente_(d.email, '✅ Cita confirmada · ' + fechaLarga_(inicio),
    '<p>Hola ' + esc_(d.nombre) + ',</p>' +
    '<p>Su cita para <b>' + esc_(d.tratamiento) + '</b> queda <b>confirmada</b> para el <b>' + fechaLarga_(inicio) + '</b>.</p>' +
    '<p>Profesional: <b>' + esc_(d.profesionalNombre || 'Sin asignar') + '</b>.</p>' +
    (mensaje ? '<p style="background:#faf6ef;padding:12px;border-left:3px solid #c2a165">' + esc_(mensaje) + '</p>' : '') +
    '<p>📍 ' + CONFIG.DIRECCION + '</p>' +
    '<p>Si necesita cambiarla o cancelarla, avísenos en el ' + CONFIG.TELEFONO +
    ' o por <a href="' + CONFIG.WHATSAPP + '">WhatsApp</a>.</p>');
}

function emailRechazada_(d, inicio, mensaje) {
  enviarCliente_(d.email, 'Sobre su solicitud de cita del ' + fechaLarga_(inicio),
    '<p>Hola ' + esc_(d.nombre) + ',</p>' +
    '<p>Lamentablemente no podemos atenderle el <b>' + fechaLarga_(inicio) + '</b> para <b>' + esc_(d.tratamiento) + '</b>.</p>' +
    '<p>Profesional: <b>' + esc_(d.profesionalNombre || 'Sin asignar') + '</b>.</p>' +
    (mensaje ? '<p style="background:#faf6ef;padding:12px;border-left:3px solid #c2a165">' + esc_(mensaje) + '</p>' : '') +
    '<p>Puede elegir otra fecha en <a href="' + CONFIG.WEB + '">nuestra web</a> o escribirnos por ' +
    '<a href="' + CONFIG.WHATSAPP + '">WhatsApp</a> y le buscamos un hueco.</p>');
}

function enviarCliente_(to, asunto, cuerpo) {
  try {
    MailApp.sendEmail({ to: to, subject: asunto, htmlBody: plantilla_(CONFIG.NOMBRE_CLINICA, cuerpo), name: CONFIG.NOMBRE_CLINICA });
  } catch (e) { console.error('Email a cliente fallido: ' + e); }
}

function plantilla_(titulo, cuerpo) {
  return '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#2b2622">' +
    '<h2 style="font-family:Georgia,serif;color:#a8874a;font-weight:normal;border-bottom:1px solid #e8dcc6;padding-bottom:8px">' + titulo + '</h2>' +
    cuerpo +
    '<p style="color:#999;font-size:12px;margin-top:28px">' + CONFIG.NOMBRE_CLINICA + ' · ' + CONFIG.DIRECCION + ' · ' + CONFIG.TELEFONO + '</p></div>';
}
function fila_(k, v) { return '<tr><td style="color:#888;padding-right:14px">' + k + '</td><td><b>' + esc_(v) + '</b></td></tr>'; }
function boton_(url, txt, color) {
  return '<a href="' + url + '" style="background:' + color + ';color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:bold;display:inline-block">' + txt + '</a>';
}


/* ============================================================
 *  4. UTILIDADES
 * ============================================================ */
function leerDatos_(e) {
  let raw = {};
  if (e && e.postData && e.postData.contents && /json/i.test(e.postData.type || '')) {
    raw = JSON.parse(e.postData.contents);
  } else if (e && e.postData && e.postData.contents && (e.postData.contents.trim().charAt(0) === '{')) {
    try { raw = JSON.parse(e.postData.contents); } catch (x) { raw = (e && e.parameter) || {}; }
  } else {
    raw = (e && e.parameter) || {};
  }
  const C = CONFIG.CAMPOS, txt = v => String(v == null ? '' : v).trim();
  const pv = txt(raw[C.primeraVisita]).toLowerCase();
  return {
    nombre: txt(raw[C.nombre]).slice(0, 100),
    telefono: txt(raw[C.telefono]).replace(/[^\d+]/g, '').slice(0, 20),
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(txt(raw[C.email])) ? txt(raw[C.email]) : '',
    tratamiento: txt(raw[C.tratamiento]).slice(0, 120),
    profesional: txt(raw[C.profesional]).slice(0, 60),
    fecha: txt(raw[C.fecha]),
    hora: txt(raw[C.hora]),
    primeraVisita: ['true', 'sí', 'si', 'on', '1', 'yes'].indexOf(pv) > -1,
    comentarios: txt(raw[C.comentarios]).slice(0, 1000),
    honeypot: txt(raw[C.honeypot]),
    requestId: /^[A-Za-z0-9_-]{16,80}$/.test(txt(raw.requestId)) ? txt(raw.requestId) : ''
  };
}

/** "2026-10-15" o "15/10/2026" + "10:30" → Date en la zona horaria del script. */
function parsearFechaHora_(fecha, hora) {
  if (fecha instanceof Date) fecha = Utilities.formatDate(fecha, zona_(), 'yyyy-MM-dd');
  let y, m, d;
  let mt = String(fecha).match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (mt) { y = +mt[1]; m = +mt[2]; d = +mt[3]; }
  else if ((mt = String(fecha).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/))) { d = +mt[1]; m = +mt[2]; y = +mt[3]; }
  else return null;
  if (hora instanceof Date) hora = Utilities.formatDate(hora, zona_(), 'HH:mm');
  const h = String(hora).match(/^(\d{1,2}):(\d{2})$/);
  if (!h) return null;
  // Se construye como texto con el desfase horario real de ese día (horario de verano/invierno)
  const base = new Date(Date.UTC(y, m - 1, d, 12));
  const offset = Utilities.formatDate(base, zona_(), 'XXX'); // p. ej. +02:00
  const iso = y + '-' + pad_(m) + '-' + pad_(d) + 'T' + pad_(+h[1]) + ':' + h[2] + ':00' + offset;
  const fechaFinal = new Date(iso);
  if (isNaN(fechaFinal)) return null;
  return Utilities.formatDate(fechaFinal, zona_(), 'yyyy-MM-dd HH:mm') === y + '-' + pad_(m) + '-' + pad_(d) + ' ' + pad_(+h[1]) + ':' + h[2] ? fechaFinal : null;
}

function fechaLarga_(dt) {
  if (!dt) return '';
  const p = Utilities.formatDate(dt, zona_(), 'u|d|M|HH:mm').split('|'); // u: 1=lunes … 7=domingo
  return DIAS[(+p[0]) % 7] + ' ' + p[1] + ' de ' + MESES[+p[2] - 1] + ' a las ' + p[3];
}

// Calendar guarda los datos del cliente. Las propiedades del script solo indexan
// códigos, estados y eventos; no requieren una hoja de cálculo.
function guardarIndice_(registro) {
  PropertiesService.getScriptProperties().setProperty('RESERVA_' + registro.id, JSON.stringify(registro));
}
function indices_() {
  const props = PropertiesService.getScriptProperties().getProperties();
  return Object.keys(props).filter(k => /^RESERVA_[A-F0-9]{8}$/.test(k)).map(k => JSON.parse(props[k]));
}
function purgarIndices_() {
  const props = PropertiesService.getScriptProperties();
  indices_().filter(r => r.creada < Date.now() - 180 * 86400000).forEach(r => props.deleteProperty('RESERVA_' + r.id));
}
function buscarRequest_(requestId) { return indices_().find(r => r.requestId === requestId); }
function buscarReserva_(id) {
  if (!/^[A-F0-9]{8}$/.test(id)) return null;
  const raw = PropertiesService.getScriptProperties().getProperty('RESERVA_' + id);
  if (!raw) return null;
  const registro = JSON.parse(raw);
  let evento = null;
  try { evento = calendario_().getEventById(registro.eventId); } catch (e) {}
  const datos = evento ? {profesionalNombre: evento.getTag('profesionalNombre'), nombre: evento.getTag('clienteNombre'), email: evento.getTag('clienteEmail'), telefono: evento.getTag('clienteTelefono'), tratamiento: evento.getTag('tratamientoNombre'), fecha: Utilities.formatDate(evento.getStartTime(), zona_(), 'dd/MM/yyyy'), hora: Utilities.formatDate(evento.getStartTime(), zona_(), 'HH:mm')} : null;
  return {registro: registro, evento: evento, datos: datos};
}

function calendario_() {
  const cal = CONFIG.CALENDAR_ID === 'primary' ? CalendarApp.getDefaultCalendar() : CalendarApp.getCalendarById(CONFIG.CALENDAR_ID);
  if (!cal) throw new Error('No encuentro el calendario: ' + CONFIG.CALENDAR_ID);
  return cal;
}

function urlAccion_(id, token, accion) {
  const base = CONFIG.WEB_APP_URL || ScriptApp.getService().getUrl();
  return base + '?id=' + encodeURIComponent(id) + '&t=' + token + '&accion=' + accion;
}

function zona_() { return 'Europe/Madrid'; }
function pad_(n) { return (n < 10 ? '0' : '') + n; }
function esc_(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}


/* ============================================================
 *  5. PRUEBA MANUAL
 *  Ejecuta esta función una vez desde el editor (botón ▶) para dar permisos
 *  y comprobar que se crea el evento y llega el email.
 * ============================================================ */
function prepararPruebas() {
  const url = CONFIG.WEB_APP_URL || ScriptApp.getService().getUrl();
  if (!url || !/\/exec$/.test(url)) throw new Error('Primero despliegue el proyecto como aplicación web.');
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('CALENDAR_ID')) {
    const cal = CalendarApp.createCalendar('Innovae — pruebas de reservas', {timeZone: 'Europe/Madrid'});
    props.setProperty('CALENDAR_ID', cal.getId());
    CONFIG.CALENDAR_ID = cal.getId();
  }
  Logger.log('Calendario de pruebas preparado. Ejecute probarReserva para crear una solicitud y enviar el correo.');
}
function probarReserva() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('CALENDAR_ID')) throw new Error('Ejecute primero prepararPruebas.');
  let manana = new Date(Date.now() + 86400000);
  while (+Utilities.formatDate(manana, zona_(), 'u') === 7) manana = new Date(manana.getTime() + 86400000);
  const f = Utilities.formatDate(manana, zona_(), 'yyyy-MM-dd');
  const e = {parameter: {nombre: 'Prueba Sistema', telefono: '600000000', email: CONFIG.EMAIL_AVISOS,
    tratamiento: 'Limpieza Facial', fecha: f, hora: '11:00', primeraVisita: 'true', comentarios: 'PRUEBA: no corresponde a un paciente', requestId: Utilities.getUuid().replace(/-/g, '')}};
  Logger.log(doPost(e).getContent());
}

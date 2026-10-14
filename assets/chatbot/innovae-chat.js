/*!
 * Chat de Clínica Innovae · widget independiente
 *
 * Uso (una sola línea antes de </body> en index.html):
 *   <script src="https://TU-SERVICIO.run.app/widget/innovae-chat.js" defer></script>
 *
 * Opciones (atributos data-* en esa misma etiqueta, todos opcionales):
 *   data-api="https://TU-SERVICIO.run.app"   origen del backend (por defecto, el del propio script)
 *   data-posicion="derecha" | "izquierda"     lado de la pantalla (por defecto derecha)
 *   data-margen-inferior="96"                 px desde abajo (para no tapar otro botón flotante)
 *
 * Va dentro de un Shadow DOM: sus estilos no afectan a la web ni la web a él.
 */
(function () {
  'use strict';
  if (window.__innovaeChat) return;
  window.__innovaeChat = true;

  var script = document.currentScript || document.querySelector('script[src*="innovae-chat"]');
  var ds = (script && script.dataset) || {};
  var ajustes = window.INNOVAE_CHAT_CONFIG || {};
  var API = (ds.api || ajustes.api || (script && !ds.conocimiento ? new URL(script.src, location.href).origin : '')).replace(/\/$/, '');
  var INFO = ds.conocimiento ? new URL(ds.conocimiento, script.src).href : '';
  var conocimiento;
  var LADO = ds.posicion === 'izquierda' ? 'left' : 'right';
  var MARGEN = parseInt(ds.margenInferior || '24', 10) || 24;
  var CLAVE = 'innovae-chat-v2-' + (API || 'informacion');

  var BIENVENIDA = 'Hola, soy el asistente virtual de **Clínica Innovae** ✨ ' +
    'Puedo resolver dudas sobre tratamientos y productos o ayudarle a pedir cita. ¿En qué le ayudo?';
  var SUGERENCIAS = ['Quiero pedir cita', '¿Qué tratamientos hacéis?', 'Horario y ubicación'];
  if (!API) BIENVENIDA = 'Hola, puedo ayudarle a consultar información sobre la clínica, sus tratamientos y productos. ' +
    'Esta versión ofrece respuestas de información, sin IA y sin gestionar citas. ¿Qué desea consultar?';

  // ---------------------------------------------------------------- estado
  function cargar() {
    try { return JSON.parse(sessionStorage.getItem(CLAVE)) || null; } catch (e) { return null; }
  }
  function guardar() {
    try { sessionStorage.setItem(CLAVE, JSON.stringify(estado)); } catch (e) { /* sin almacenamiento */ }
  }
  function nuevoId() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID().replace(/-/g, '');
    return (Date.now().toString(36) + Math.random().toString(36).slice(2, 12)).slice(0, 24);
  }
  var estado = cargar() || { sesion: nuevoId(), mensajes: [], abierto: false };
  if (!Array.isArray(estado.mensajes) || !/^[A-Za-z0-9_-]{8,64}$/.test(estado.sesion || '')) {
    estado = { sesion: nuevoId(), mensajes: [], abierto: false };
  }
  estado.mensajes = estado.mensajes.filter(function (m) { return m && typeof m.texto === 'string'; }).slice(-50);

  // ------------------------------------------------------------------- UI
  var host = document.createElement('div');
  host.id = 'innovae-chat';
  document.body.appendChild(host);
  var root = host.attachShadow({ mode: 'open' });

  root.innerHTML =
    '<style>' +
    ':host{all:initial}' +
    '*{box-sizing:border-box}' +
    '.w{--oro:#b8965a;--oro-osc:#957443;--crema:#f8f3ec;--crema-2:#efe6d8;--tinta:#1d1a16;--gris:#6f675c;' +
    'position:fixed;' + LADO + ':20px;bottom:' + MARGEN + 'px;z-index:2147483000;' +
    'font-family:Montserrat,system-ui,-apple-system,"Segoe UI",sans-serif;color:var(--tinta)}' +
    '.lanzador{width:60px;height:60px;border-radius:50%;border:1px solid rgba(255,255,255,.35);cursor:pointer;' +
    'background:var(--oro);color:#fff;box-shadow:0 8px 24px rgba(0,0,0,.3);display:grid;place-items:center;' +
    'transition:transform .2s}' +
    '.lanzador:hover{transform:scale(1.06)}.lanzador:focus-visible{outline:2px solid var(--oro);outline-offset:3px}' +
    '.lanzador svg{width:28px;height:28px}' +
    '.panel{position:absolute;' + LADO + ':0;bottom:76px;width:370px;max-width:calc(100vw - 32px);' +
    'height:560px;max-height:calc(100vh - ' + (MARGEN + 100) + 'px);background:var(--crema);border-radius:18px;' +
    'box-shadow:0 18px 48px rgba(0,0,0,.28);display:none;flex-direction:column;overflow:hidden;' +
    'border:1px solid rgba(184,150,90,.35)}' +
    '.panel.abierto{display:flex;animation:entra .22s ease-out}' +
    '@keyframes entra{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}' +
    '.cab{background:var(--tinta);color:#fff;padding:14px 16px;display:flex;align-items:center;gap:12px}' +
    '.logo{width:38px;height:38px;border-radius:50%;border:1px solid var(--oro);display:grid;place-items:center;' +
    'color:var(--oro);font-family:"Cormorant Garamond",Georgia,serif;font-size:20px;font-style:italic}' +
    '.cab h2{margin:0;font-family:"Cormorant Garamond",Georgia,serif;font-weight:500;font-size:21px;letter-spacing:.3px}' +
    '.cab p{margin:2px 0 0;font-size:11px;color:#cfc6b8;letter-spacing:.4px}' +
    '.cab .acc{margin-left:auto;display:flex;gap:4px}' +
    '.ico{background:none;border:0;color:#cfc6b8;cursor:pointer;padding:6px;border-radius:8px;font-size:12px}' +
    '.ico:hover{color:var(--oro)}.ico:focus-visible{outline:2px solid var(--oro)}' +
    '.lista{flex:1;overflow-y:auto;padding:16px 14px;display:flex;flex-direction:column;gap:10px}' +
    '.m{max-width:85%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;' +
    'white-space:pre-wrap;overflow-wrap:anywhere}' +
    '.m.bot{background:#fff;border:1px solid var(--crema-2);border-bottom-left-radius:4px;align-self:flex-start}' +
    '.m.yo{background:var(--tinta);color:#fff;border-bottom-right-radius:4px;align-self:flex-end}' +
    '.m.err{background:#fbeceb;border-color:#f0cfcc}' +
    '.m a{color:var(--oro-osc)}.m.yo a{color:var(--oro)}' +
    '.chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 14px 10px}' +
    '.chip{border:1px solid var(--oro);background:transparent;color:var(--oro-osc);border-radius:999px;' +
    'padding:6px 12px;font:inherit;font-size:12.5px;cursor:pointer}' +
    '.chip:hover{background:var(--oro);color:#fff}' +
    '.escribe{display:flex;gap:4px;padding:12px 14px}' +
    '.escribe i{width:7px;height:7px;border-radius:50%;background:var(--oro);opacity:.4;animation:pt 1.2s infinite}' +
    '.escribe i:nth-child(2){animation-delay:.2s}.escribe i:nth-child(3){animation-delay:.4s}' +
    '@keyframes pt{0%,60%,100%{opacity:.3;transform:none}30%{opacity:1;transform:translateY(-3px)}}' +
    'form{display:flex;gap:8px;padding:10px 12px;border-top:1px solid var(--crema-2);background:#fff}' +
    'textarea{flex:1;resize:none;border:1px solid var(--crema-2);border-radius:12px;padding:10px 12px;' +
    'font:inherit;font-size:14px;max-height:110px;background:var(--crema);color:var(--tinta)}' +
    'textarea:focus{outline:none;border-color:var(--oro)}' +
    '.enviar{width:42px;border:0;border-radius:12px;background:var(--oro);color:#fff;cursor:pointer;' +
    'display:grid;place-items:center}.enviar:disabled{opacity:.45;cursor:default}' +
    '.enviar svg{width:18px;height:18px}' +
    '.pie{font-size:10.5px;color:var(--gris);text-align:center;padding:0 12px 8px;background:#fff}' +
    '@media (max-width:480px){.w{' + LADO + ':12px}.panel{position:fixed;inset:auto 8px ' + (MARGEN + 76) + 'px 8px;' +
    'width:auto;max-width:none;height:auto;top:12px;max-height:none}}' +
    '@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}' +
    '</style>' +
    '<div class="w">' +
    '  <section class="panel" role="dialog" aria-label="Chat con Clínica Innovae" aria-modal="false">' +
    '    <header class="cab"><div class="logo" aria-hidden="true">I</div>' +
    '      <div><h2>Clínica Innovae</h2><p>' + (API ? 'Asistente virtual con IA' : 'Información de la clínica · sin IA') + '</p></div>' +
    '      <div class="acc"><button class="ico reiniciar" type="button" title="Nueva conversación">Reiniciar</button>' +
    '      <button class="ico cerrar" type="button" aria-label="Cerrar chat">✕</button></div></header>' +
    '    <div class="lista" aria-live="polite"></div>' +
    '    <div class="chips"></div>' +
    '    <form><textarea rows="1" maxlength="1000" placeholder="Escriba su mensaje…" aria-label="Mensaje"></textarea>' +
    '      <button class="enviar" type="submit" aria-label="Enviar"><svg viewBox="0 0 24 24" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg></button></form>' +
    '    <div class="pie">' + (API ? 'Asistente con IA' : 'Respuestas de información') + ' · No comparta datos de salud</div>' +
    '  </section>' +
    '  <button class="lanzador" type="button" aria-label="Abrir chat" aria-expanded="false">' +
    '    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" ' +
    'stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>' +
    '<path d="M8.5 11h.01M12 11h.01M15.5 11h.01"/></svg></button>' +
    '</div>';

  var $ = function (s) { return root.querySelector(s); };
  var panel = $('.panel'), lista = $('.lista'), chips = $('.chips'), form = $('form'),
      entrada = $('textarea'), botonEnviar = $('.enviar'), lanzador = $('.lanzador');
  var ocupado = false;

  // Markdown mínimo y SEGURO: se escapa todo y luego se permite **negrita**, *negrita* y enlaces.
  function formatear(texto) {
    var contenedor = document.createElement('div'), t = String(texto), pos = 0;
    var patron = /\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)|https?:\/\/[^\s<>"«»]+|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*/g;
    var m;
    while ((m = patron.exec(t))) {
      contenedor.appendChild(document.createTextNode(t.slice(pos, m.index)));
      if (m[3] || m[4]) {
        var fuerte = document.createElement('strong'); fuerte.textContent = m[3] || m[4]; contenedor.appendChild(fuerte);
      } else {
        var url = m[2] || m[0], resto = '';
        if (!m[2]) { resto = (url.match(/[.,;:!?]+$/) || [''])[0]; url = url.slice(0, url.length - resto.length); }
        var a = document.createElement('a'); a.href = url; a.textContent = m[1] || url;
        a.target = '_blank'; a.rel = 'noopener noreferrer'; contenedor.appendChild(a);
        if (resto) contenedor.appendChild(document.createTextNode(resto));
      }
      pos = patron.lastIndex;
    }
    contenedor.appendChild(document.createTextNode(t.slice(pos)));
    return contenedor.innerHTML;
  }

  function pintarMensaje(m) {
    var div = document.createElement('div');
    div.className = 'm ' + (m.de === 'yo' ? 'yo' : 'bot') + (m.error ? ' err' : '');
    div.innerHTML = formatear(m.texto);
    lista.appendChild(div);
    lista.scrollTop = lista.scrollHeight;
  }

  function pintarChips() {
    chips.innerHTML = '';
    if (estado.mensajes.some(function (m) { return m.de === 'yo'; })) return;
    SUGERENCIAS.forEach(function (s) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'chip'; b.textContent = s;
      b.addEventListener('click', function () { enviar(s); });
      chips.appendChild(b);
    });
  }

  function pintarTodo() {
    lista.innerHTML = '';
    pintarMensaje({ de: 'bot', texto: BIENVENIDA });
    estado.mensajes.forEach(pintarMensaje);
    pintarChips();
  }

  function abrir(si) {
    estado.abierto = si;
    panel.classList.toggle('abierto', si);
    lanzador.setAttribute('aria-expanded', String(si));
    lanzador.setAttribute('aria-label', si ? 'Cerrar chat' : 'Abrir chat');
    guardar();
    if (si) { lista.scrollTop = lista.scrollHeight; setTimeout(function () { entrada.focus(); }, 50); }
  }

  function indicador(mostrar) {
    var previo = root.querySelector('.escribe');
    if (previo) previo.remove();
    if (mostrar) {
      var d = document.createElement('div');
      d.className = 'escribe'; d.setAttribute('aria-label', 'Escribiendo');
      d.innerHTML = '<i></i><i></i><i></i>';
      lista.appendChild(d); lista.scrollTop = lista.scrollHeight;
    }
  }

  function anadir(m) { estado.mensajes.push(m); estado.mensajes = estado.mensajes.slice(-50); guardar(); pintarMensaje(m); pintarChips(); }

  function normalizar(t) {
    return String(t).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function responderInformacion(texto) {
    if (!conocimiento) conocimiento = fetch(INFO).then(function (r) {
      if (!r.ok) throw new Error('Información no disponible');
      return r.json();
    }).catch(function (e) { conocimiento = null; throw e; });
    return conocimiento.then(function (datos) {
      var q = normalizar(texto), contacto = '\nPuede llamar al 661 73 48 70 o escribir por WhatsApp: https://wa.me/34661734870';
      if (/dificultad.*respirar|no puedo respirar|dolor intenso|hinchazon importante/.test(q)) {
        return 'Si tiene síntomas graves, llame al 112. Contacte también con la clínica. Este chat no puede valorar síntomas.' + contacto;
      }
      if (/embaraz|lactancia|alergia|medicacion|enfermedad|reaccion|irritacion|dolor|puedo usar|puedo hacer|me recomiendas|soy apt|para mi piel/.test(q)) {
        return 'La idoneidad de un tratamiento o producto para su caso debe valorarla un profesional. No puedo valorar síntomas ni recomendar tratamientos personalizados.' + contacto;
      }
      if (/reserv|cita|disponibilidad|hueco|cancel|anular/.test(q)) return datos.faq.reservas + contacto;
      if (/precio|cuesta|cuestan|coste|cuanto vale|tarifa|oferta/.test(q)) return datos.faq.precios + contacto;
      if (/horario|abri|abr[ei]s|cierr|hora.*(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo)/.test(q)) {
        return datos.faq.horario + (/ubicacion|direccion|donde|ubicad/.test(q) ? '\n\n' + datos.faq.direccion : '');
      }
      if (/ubicacion|direccion|donde|ubicad|como llegar/.test(q)) return datos.faq.direccion;
      if (/telefono|contact|whatsapp|hablar.*persona/.test(q)) return 'El equipo de la clínica le atenderá directamente.' + contacto;
      if (/equipo|doctor|romero|profesional/.test(q)) return datos.faq.equipo + contacto;
      if (/envio|enviar|recog|domicilio/.test(q)) return datos.faq.tienda + contacto;
      var palabras = q.split(' ').filter(function (p) { return p.length > 2 && !/^(que|como|para|una|con|los|las|del|por|sobre|quiero|informacion|explica|saber|teneis|haceis|tratamiento|tratamientos|producto|productos|crema)$/.test(p); });
      var articulos = datos.articulos.map(function (a) {
        var n = normalizar(a.nombre + ' ' + (a.alias || ''));
        var score = palabras.reduce(function (v, p) { return v + ((' ' + n + ' ').includes(' ' + p + ' ') ? 1 : 0); }, 0);
        if ((' ' + q + ' ').includes(' ' + normalizar(a.nombre) + ' ')) score += 100;
        return {articulo:a, score:score};
      }).filter(function (a) { return a.score > 0; }).sort(function (a,b) { return b.score - a.score; });
      var mejor = articulos.length ? articulos[0].score : 0;
      var candidatos = articulos.filter(function (a) { return a.score === mejor; });
      var a = candidatos.length === 1 ? candidatos[0].articulo : null;
      if (!a && !articulos.length && /cuanto dura|como se usa|beneficio|mas detalle/.test(q)) {
        a = datos.articulos.find(function (x) { return x.nombre === estado.tema; });
      }
      if (a) { estado.tema = a.nombre; guardar(); return '**' + a.nombre + '**\n' + a.texto + (a.url ? '\n\nVer ficha: ' + a.url : ''); }
      if (candidatos.length > 1) return 'He encontrado varias opciones. Escriba el nombre de la que quiere consultar:\n' + candidatos.map(function (a) {return '• ' + a.articulo.nombre;}).join('\n');
      if (/tratamiento|servicio|medicina estetica|estetica facial|estetica corporal/.test(q)) {
        var categoria = /medicina estetica/.test(q) ? 'Medicina Estética' : /estetica facial/.test(q) ? 'Estética Facial' : /estetica corporal/.test(q) ? 'Estética Corporal' : '';
        return 'Puede consultar estos tratamientos:\n' + datos.articulos.filter(function (a) {return a.tipo==='tratamiento' && (!categoria || a.categoria===categoria);}).map(function (a) {return '• '+a.nombre;}).join('\n') + '\n\nEscriba el nombre de uno para ver su información.';
      }
      if (/producto|tienda|cosmetica|crema|serum/.test(q)) return 'Estos son los productos del catálogo:\n' + datos.articulos.filter(function (a) {return a.tipo==='producto';}).map(function (a) {return '• '+a.nombre;}).join('\n') + '\n\nEscriba el nombre de uno para ver su información.';
      if (/^(hola|buenas|buenos dias|buenas tardes|gracias)$/.test(q)) return 'Hola. Puedo mostrarle información de horarios, ubicación, tratamientos y productos. ¿Qué desea consultar?';
      return 'No encuentro una respuesta en la información disponible. Esta versión sin IA reconoce consultas de horarios, ubicación y nombres de tratamientos o productos.' + contacto;
    });
  }

  function enviar(texto) {
    texto = (texto || '').trim();
    if (!texto || ocupado) return;
    ocupado = true; botonEnviar.disabled = true; $('.reiniciar').disabled = true;
    anadir({ de: 'yo', texto: texto });
    entrada.value = ''; ajustarAltura();
    indicador(true);

    var ctrl = window.AbortController ? new AbortController() : null;
    var temporizador = setTimeout(function () { if (ctrl) ctrl.abort(); }, 180000);

    var peticion = API ? fetch(API + '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sesion_id: estado.sesion, mensaje: texto }),
      signal: ctrl ? ctrl.signal : undefined
    }) : responderInformacion(texto).then(function (respuesta) {
      return { ok: true, json: function () { return Promise.resolve({respuesta: respuesta}); } };
    });
    peticion
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (j) { return { r: r, j: j }; });
      })
      .then(function (x) {
        if (x.j && x.j.respuesta) anadir({ de: 'bot', texto: x.j.respuesta, error: !x.r.ok });
        else throw new Error('HTTP ' + x.r.status);
      })
      .catch(function () {
        anadir({ de: 'bot', error: true, texto: 'No he podido conectar ahora mismo. Puede escribirnos por ' +
          'WhatsApp (https://wa.me/34661734870) o llamar al 661 73 48 70.' });
      })
      .then(function () {
        clearTimeout(temporizador); indicador(false);
        ocupado = false; botonEnviar.disabled = false; $('.reiniciar').disabled = false;
        if (estado.abierto) entrada.focus();
      });
  }

  function ajustarAltura() { entrada.style.height = 'auto'; entrada.style.height = Math.min(entrada.scrollHeight, 110) + 'px'; }

  // --------------------------------------------------------------- eventos
  lanzador.addEventListener('click', function () { abrir(!estado.abierto); });
  $('.cerrar').addEventListener('click', function () { abrir(false); lanzador.focus(); });
  $('.reiniciar').addEventListener('click', function () {
    estado = { sesion: nuevoId(), mensajes: [], abierto: true }; guardar(); pintarTodo(); entrada.focus();
  });
  form.addEventListener('submit', function (e) { e.preventDefault(); enviar(entrada.value); });
  entrada.addEventListener('input', ajustarAltura);
  entrada.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(entrada.value); }
  });
  root.addEventListener('keydown', function (e) { if (e.key === 'Escape' && estado.abierto) abrir(false); });

  // API pública mínima, por si quieres abrir el chat desde un botón de la web:
  //   <button onclick="InnovaeChat.abrir('Quiero pedir cita para Limpieza Facial')">…</button>
  window.InnovaeChat = {
    abrir: function (mensaje) { abrir(true); if (mensaje) enviar(mensaje); },
    cerrar: function () { abrir(false); }
  };

  pintarTodo();
  if (estado.abierto) abrir(true);
})();

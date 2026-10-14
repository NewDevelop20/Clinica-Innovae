(function () {
  'use strict';
  var form = document.getElementById('bookingForm');
  if (!form) return;
  var ajustes = window.INNOVAE_RESERVAS_CONFIG || {};
  var endpoint = ajustes.endpoint || '';
  var modoPruebas = ajustes.modoPruebas === true;
  if (modoPruebas) {
    var notaPruebas = document.createElement('p');
    notaPruebas.id = 'bookingTestNotice';
    notaPruebas.textContent = 'Formulario en pruebas: no reserve una cita real aquí. Para pedir cita, llame al 661 73 48 70.';
    notaPruebas.style.cssText = 'color:#e8d3aa;border:1px solid #b8965a;padding:16px;margin-bottom:20px;font-size:.9rem;line-height:1.6';
    form.before(notaPruebas);
  }
  var configurado = /^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(endpoint);
  var $ = function (id) { return document.getElementById(id); };
  var nombre=$('r-nombre'), telefono=$('r-telefono'), email=$('r-email'), tratamiento=$('r-tratamiento'), fecha=$('r-fecha'), hora=$('r-hora'), rgpd=$('r-rgpd'), submit=$('r-submit');
  var estado=document.createElement('p'); estado.id='bookingStatus'; estado.setAttribute('role','status'); estado.style.cssText='color:#e8d3aa;font-size:.85rem;line-height:1.6'; form.prepend(estado);
  var envio=false, secuencia=0, ultimaConsulta='', idSolicitud='', firmaSolicitud='';
  function aviso(t) { estado.textContent=t; }
  function id() { return 'r_' + (crypto.randomUUID ? crypto.randomUUID().replace(/-/g,'') : Date.now().toString(36)+Math.random().toString(36).slice(2)+Math.random().toString(36).slice(2)); }
  function madrid() {
    var parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Madrid',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
    var p={};parts.forEach(function(x){p[x.type]=x.value;});return {dia:p.year+'-'+p.month+'-'+p.day,minutos:+p.hour*60 + +p.minute};
  }
  fecha.min=madrid().dia;var max=new Date(fecha.min+'T12:00:00Z');max.setUTCDate(max.getUTCDate()+90);fecha.max=max.toISOString().slice(0,10);
  function opciones(lista, texto) {
    hora.replaceChildren();var vacia=new Option(texto,'',true,true);vacia.disabled=true;hora.add(vacia);
    lista.forEach(function(h){hora.add(new Option(h,h));});hora.disabled=!lista.length;
  }
  function posibles(d) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d) || d<fecha.min || d>fecha.max) return [];
    var dow=new Date(d+'T12:00:00Z').getUTCDay();var periodos=dow===0?[]:dow===6?[[630,780]]:[[600,810],[990,1230]], horas=[],now=madrid();
    periodos.forEach(function(p){for(var m=p[0];m+60<=p[1];m+=30){if(d===now.dia && m<now.minutos+60)continue;horas.push(String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0'));}});return horas;
  }
  // JSONP solo consulta disponibilidad; ningún dato del cliente viaja en la URL.
  function disponibilidad(d,t) {
    return new Promise(function(resolve,reject){
      var callback='innovaeAvailability_'+id().replace(/-/g,'_'), script=document.createElement('script'),timer;
      function limpiar(){clearTimeout(timer);script.remove();delete window[callback];}
      window[callback]=function(res){limpiar();if(!res || res.ok!==true || !Array.isArray(res.bloqueadas))reject(new Error(res && res.error || 'Respuesta de agenda no válida.'));else resolve(res);};
      script.onerror=function(){limpiar();reject(new Error('No se pudo consultar la agenda.'));};
      timer=setTimeout(function(){limpiar();reject(new Error('La agenda no ha respondido. Inténtelo de nuevo.'));},20000);
      var url=new URL(endpoint);url.searchParams.set('disponibilidad',d);url.searchParams.set('tratamiento',t);url.searchParams.set('callback',callback);script.src=url.href;document.head.appendChild(script);
    });
  }
  function actualizar() {
    var orden=++secuencia;ultimaConsulta='';submit.disabled=true;opciones([],'Seleccione tratamiento y fecha');
    if(!configurado){aviso('La reserva online todavía no está conectada. Para pedir cita, llame al 661 73 48 70.');return;}
    if(!fecha.value || !tratamiento.value)return;
    var fechas=posibles(fecha.value);
    if(!fechas.length){aviso('Seleccione una fecha y hora dentro del horario de apertura, con al menos una hora de antelación.');return;}
    var d=fecha.value,t=tratamiento.value;aviso('Consultando disponibilidad…');
    disponibilidad(d,t).then(function(res){if(orden!==secuencia)return;var libres=fechas.filter(function(h){return !res.bloqueadas.includes(h);});opciones(libres,libres.length?'Seleccione una hora':'No quedan horas disponibles');ultimaConsulta=d+'|'+t;submit.disabled=!libres.length;aviso(libres.length?'La clínica revisará su solicitud antes de confirmar la cita.':'No quedan horas libres. Seleccione otro día.');}).catch(function(e){if(orden!==secuencia)return;aviso(e.message+' Puede llamar al 661 73 48 70.');});
  }
  function error(el,invalid){var group=el.closest('.form-group');if(group)group.classList.toggle('invalid',invalid);return !invalid;}
  nombre.addEventListener('input',function(){this.value=this.value.replace(/[^\p{L}\s'’.-]/gu,'');error(this,false);});
  telefono.addEventListener('input',function(){this.value=this.value.replace(/\D/g,'');error(this,false);});
  [email,rgpd,hora].forEach(function(el){el.addEventListener('change',function(){error(el,false);});});
  [fecha,tratamiento].forEach(function(el){el.addEventListener('change',function(){error(el,false);actualizar();});});
  form.querySelectorAll('input[name="primera"]').forEach(function(r){r.addEventListener('change',function(){error(r,false);var si=r.value==='Sí';$('firstVisitNote').classList.toggle('show',si);if(si)tratamiento.value='Primera consulta / valoración';else if(tratamiento.value==='Primera consulta / valoración')tratamiento.value='';actualizar();});});
  function validar() {
    var validos=[error(nombre,nombre.value.trim().length<2),error(telefono,!/^\d{9,15}$/.test(telefono.value)),error(email,!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())),error(tratamiento,!tratamiento.value),error(fecha,!posibles(fecha.value).length),error(hora,!hora.value || hora.disabled),error(rgpd,!rgpd.checked),error(form.querySelector('input[name="primera"]'),!form.querySelector('input[name="primera"]:checked'))];
    var invalid=form.querySelector('.invalid input,.invalid select');if(invalid)invalid.focus();return validos.every(Boolean);
  }
  // El formulario POST oculta la respuesta HTML de Apps Script en un iframe.
  // Solo se acepta un mensaje del dominio Google con el ID aleatorio esperado.
  function registrar(datos) {
    return new Promise(function(resolve,reject){
      var marco=document.createElement('iframe'),post=document.createElement('form'),timer;marco.name='reserva_'+datos.requestId;marco.hidden=true;post.hidden=true;post.method='POST';post.action=endpoint;post.target=marco.name;
      Object.keys(datos).forEach(function(k){var input=document.createElement('input');input.type='hidden';input.name=k;input.value=datos[k];post.appendChild(input);});
      function limpiar(){clearTimeout(timer);window.removeEventListener('message',recibir);post.remove();marco.remove();}
      function recibir(e){var host;try{host=new URL(e.origin).hostname;}catch(_){return;}if(!/^https:/.test(e.origin) || !(host==='script.google.com' || host==='script.googleusercontent.com' || host.endsWith('-script.googleusercontent.com')))return;
        if(!e.data || e.data.tipo!=='innovae-reserva' || e.data.requestId!==datos.requestId)return;
        var res=e.data.resultado;limpiar();if(res && res.ok===true && /^[A-F0-9]{8}$/.test(res.id))resolve(res);else reject(new Error(res && res.error || 'La solicitud no se ha registrado.'));}
      window.addEventListener('message',recibir);timer=setTimeout(function(){limpiar();reject(new Error('No se ha podido comprobar el envío. Puede reintentar sin cambiar los datos o contactar con la clínica.'));},45000);
      document.body.append(marco,post);post.submit();
    });
  }
  form.addEventListener('submit',function(e){e.preventDefault();if(envio)return;if(!configurado){actualizar();return;}if(!validar())return;if(ultimaConsulta!==fecha.value+'|'+tratamiento.value){actualizar();return;}
    var datos={nombre:nombre.value.trim(),telefono:telefono.value,email:email.value.trim(),tratamiento:tratamiento.value,fecha:fecha.value,hora:hora.value,primeraVisita:form.querySelector('input[name="primera"]:checked').value==='Sí'?'true':'false',comentarios:$('r-notas').value.trim(),website:$('r-website').value,transporte:'iframe'};
    var firma=JSON.stringify(datos);if(firma!==firmaSolicitud){idSolicitud=id();firmaSolicitud=firma;}datos.requestId=idSolicitud;
    envio=true;submit.disabled=true;submit.textContent='Enviando…';aviso('Registrando su solicitud…');
    registrar(datos).then(function(res){if(res.estado==='RECHAZADA')throw new Error('Esta solicitud ya fue rechazada. Contacte con la clínica para pedir otra cita.');$('bc-name').textContent=datos.nombre.split(' ')[0];$('bc-detail').textContent='Solicitud #'+res.id+' · '+datos.tratamiento+' · '+datos.fecha.split('-').reverse().join('/')+' a las '+datos.hora;
      var note=$('bc-note');note.style.display='block';note.textContent=res.aviso_enviado===false?'La solicitud está registrada, pero el aviso por correo no ha podido enviarse. Llame al 661 73 48 70 indicando su código.':(modoPruebas ? 'Solicitud de prueba registrada. No equivale a una cita real.' : 'La cita queda pendiente de confirmación por la clínica.');
      form.style.display='none';$('bookingConfirm').classList.add('show');$('bookingConfirm').scrollIntoView({behavior:'smooth',block:'center'});
    }).catch(function(e){aviso(e.message);}).finally(function(){envio=false;submit.disabled=hora.disabled;submit.textContent='Solicitar cita';});
  });
  actualizar();
})();

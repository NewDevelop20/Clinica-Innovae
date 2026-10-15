(function () {
  'use strict';
  var mapa = document.getElementById('contact-map-frame');
  var aviso = document.getElementById('map-consent');
  var boton = document.getElementById('load-map');
  if (!mapa || !aviso || !boton) return;
  var clave = 'innovae_mapa';
  function mostrar(aceptado) {
    if (aceptado) {
      if (!mapa.hasAttribute('src')) mapa.src = mapa.dataset.src;
    } else {
      mapa.removeAttribute('src');
    }
    mapa.hidden = !aceptado;
    aviso.hidden = aceptado;
  }
  function sincronizar() {
    var aceptado = false;
    try { aceptado = localStorage.getItem(clave) === 'aceptado'; } catch (e) { /* consentimiento solo para esta visita */ }
    mostrar(aceptado);
  }
  boton.addEventListener('click', function () {
    try { localStorage.setItem(clave, 'aceptado'); } catch (e) { /* permite abrir el mapa sin guardar la decisión */ }
    mostrar(true);
  });
  window.addEventListener('storage', function (e) {
    if (e.key === clave || e.key === null) sincronizar();
  });
  window.addEventListener('pageshow', sincronizar);
  sincronizar();
})();

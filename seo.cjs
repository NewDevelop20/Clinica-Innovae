// Metadatos compartidos para páginas estáticas e indexables sin JavaScript.
const base = 'https://newdevelop20.github.io/Clinica-Innovae/';
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function metadata(title, description, path = '') {
  const url = base + path;
  return `<title>${escape(title)}</title>
<meta name="description" content="${escape(description)}">
<link rel="canonical" href="${escape(url)}">
<meta property="og:locale" content="es_ES">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Clínica Innovae">
<meta property="og:title" content="${escape(title)}">
<meta property="og:description" content="${escape(description)}">
<meta property="og:url" content="${escape(url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="${escape(title)}">
<meta name="twitter:description" content="${escape(description)}">`;
}
function legalLinks(prefix = '') {
  return `<nav class="legal-links" aria-label="Información legal"><a href="${prefix}aviso-legal.html">Aviso legal</a><a href="${prefix}politica-privacidad.html">Política de privacidad</a><a href="${prefix}politica-cookies.html">Política de cookies</a></nav>`;
}
module.exports = {base, escape, metadata, legalLinks};

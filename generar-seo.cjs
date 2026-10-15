// Ejecutar después de generar-productos.cjs. Los detalles del index son la fuente.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {base, escape, metadata} = require('./seo.cjs');
const root = __dirname;
const write = (file, text) => fs.writeFileSync(path.join(root, file), text);
let index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const plain = html => html.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
const descriptions = {
  't-arrugas': 'Tratamiento de arrugas de expresión con toxina botulínica en Úbeda. Conoce en qué consiste, sus indicaciones y los cuidados posteriores.',
  't-hialuronico': 'Rellenos con ácido hialurónico en Úbeda para restaurar volúmenes y perfilar rasgos. Información sobre la valoración, la sesión y los cuidados.',
  't-hilos': 'Hilos tensores en Úbeda para mejorar la firmeza facial. Consulta en qué consiste el tratamiento, para quién está indicado y sus cuidados.',
  't-mesoterapia': 'Mesoterapia en Clínica Innovae, Úbeda. Descubre cómo se realiza, sus indicaciones para el cuidado de la piel y las recomendaciones tras la sesión.',
  't-limpieza': 'Limpieza facial profesional en Úbeda para retirar impurezas y cuidar la piel. Consulta cómo es la sesión y los cuidados recomendados.',
  't-peeling': 'Peeling mecánico en Úbeda para exfoliar la piel y mejorar su textura. Información sobre la sesión, las indicaciones y los cuidados posteriores.',
  't-hidratacion': 'Hidratación facial en Clínica Innovae, Úbeda. Conoce el tratamiento para pieles deshidratadas, cómo se realiza y los cuidados recomendados.',
  't-oxigenacion': 'Oxigenación facial en Úbeda para el cuidado y la luminosidad de la piel. Descubre sus indicaciones, cómo es la sesión y los cuidados posteriores.',
  't-vitaminac': 'Tratamiento facial con vitamina C en Úbeda. Información sobre el cuidado antioxidante, la luminosidad de la piel y el desarrollo de la sesión.',
  't-reafirmante': 'Tratamiento reafirmante en Clínica Innovae, Úbeda. Consulta sus indicaciones, cómo se trabaja la firmeza de la piel y los cuidados recomendados.',
  't-kinesiolifting': 'Kinesiolifting en Úbeda: conoce esta técnica manual de cuidado facial, sus indicaciones, cómo es la sesión y las recomendaciones posteriores.',
  't-radiofrecuencia': 'Radiofrecuencia en Clínica Innovae, Úbeda. Descubre cómo se utiliza para trabajar la firmeza de la piel y qué cuidados acompañan al tratamiento.',
  't-fotorejuvenecimiento': 'Fotorejuvenecimiento en Úbeda. Consulta en qué consiste, para qué alteraciones de la piel se utiliza y las recomendaciones antes y después.',
  't-ultrasonix': 'Tratamiento Ultrasonix en Clínica Innovae, Úbeda. Conoce sus indicaciones, el desarrollo de la sesión y los cuidados recomendados.',
  't-shr': 'Depilación SHR en Úbeda. Información sobre el tratamiento, las zonas de aplicación, cómo son las sesiones y los cuidados de la piel.',
  't-ipl': 'Depilación IPL en Clínica Innovae, Úbeda. Consulta en qué consiste la luz pulsada, sus indicaciones y los cuidados antes y después de la sesión.',
  't-maderoterapia': 'Maderoterapia en Úbeda: conoce el masaje con instrumentos de madera, sus indicaciones corporales, cómo es la sesión y los cuidados recomendados.',
  't-presoterapia': 'Presoterapia en Clínica Innovae, Úbeda. Descubre el tratamiento de compresión, sus indicaciones y cómo se desarrolla una sesión.',
  't-drenajes': 'Drenaje linfático en Úbeda. Información sobre esta técnica de masaje, sus indicaciones, el desarrollo de la sesión y las recomendaciones de cuidado.',
  't-hondas': 'Tratamiento con ondas magnéticas en Clínica Innovae, Úbeda. Consulta en qué consiste, sus indicaciones corporales y cómo se realiza la sesión.',
  't-cera': 'Depilación con cera facial y corporal en Úbeda. Conoce las zonas de aplicación, cómo es la sesión y los cuidados para la piel.',
  't-endolifting': 'Endolifting con fibra óptica en Úbeda. Conoce en qué consiste, sus indicaciones, la valoración médica previa y los cuidados posteriores.',
  't-blumed': 'Tratamiento de manchas y lesiones con Blumed en Úbeda. Consulta sus indicaciones, la valoración médica previa y los cuidados de la piel.',
  't-aranas': 'Tratamiento de arañas vasculares en Úbeda. Información sobre la valoración médica, cómo es la sesión y las recomendaciones posteriores.',
  't-dermapen': 'Dermapen en Clínica Innovae, Úbeda. Descubre la técnica de microagujas, sus indicaciones para la piel y los cuidados después del tratamiento.',
};
const homeTitle = 'Clínica Innovae | Medicina estética en Úbeda, Jaén';
const homeDescription = 'Clínica Innovae en Úbeda, Jaén: medicina estética, tratamientos faciales y corporales y cosmética profesional. Conoce al equipo y solicita tu cita.';
// Reemplaza solo los metadatos que controla este generador.
index = index.replace(/\s*<(?:title\b[^>]*>[\s\S]*?<\/title|meta\b[^>]*(?:name="(?:description|twitter:[^"]+)"|property="og:[^"]+")[^>]*|link\b[^>]*rel="canonical"[^>]*)>/g, '');
index = index.replace(/(<meta name="viewport"[^>]*>)/, '$1\n  ' + metadata(homeTitle, homeDescription));
const styles = index.match(/<style>([\s\S]*?)<\/style>/)[1].replace(/\/\* ENLACES DE FICHAS \*\/[\s\S]*$/, '');
const pages = [];
for (const match of index.matchAll(/  <div class="treatment-detail" id="([^"]+)">([\s\S]*?)\n  <\/div>/g)) {
  const [original, id, inner] = match;
  const heading = inner.match(/<h[12] class="td-title">([\s\S]*?)<\/h[12]>/);
  assert(heading, `Falta el título de ${id}`);
  const name = plain(heading[1]);
  const team = id.startsWith('p-');
  const role = team ? plain(inner.match(/<p class="profile-spec">([\s\S]*?)<\/p>/)[1]) : '';
  const description = team ? `Conoce el perfil de ${name} en Clínica Innovae, Úbeda: ${role}. Consulta su formación y experiencia.` : descriptions[id];
  assert(description, `Falta una descripción específica para ${id}`);
  const file = (team ? 'equipo/' : 'tratamientos/') + id.slice(2) + '.html';
  const title = name + (team ? ' | Equipo Innovae' : ' en Úbeda | Innovae');
  let body = inner.replace(/<h2 class="td-title">([\s\S]*?)<\/h2>/, '<h1 class="td-title">$1</h1>')
    .replace(/href="#([^"]+)"/g, 'href="../index.html#$1"')
    .replace(/\s+onclick="[^"]*"/g, '');
  body = body.replace(/<h3>/g, '<h2>').replace(/<\/h3>/g, '</h2>');
  const preselect = inner.match(/preselectTratamiento\('([^']+)'\)/);
  if (preselect) body = body.replace('href="../index.html#reservas"', `href="../index.html?tratamiento=${encodeURIComponent(preselect[1])}#reservas"`);
  fs.mkdirSync(path.join(root, path.dirname(file)), {recursive: true});
  write(file, `<!DOCTYPE html>\n<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">\n${metadata(title, description, file)}\n<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Montserrat:wght@300;400;500;600;700&display=swap" rel="stylesheet"><link rel="stylesheet" href="../assets/fichas.css"></head>\n<body><main>${body}\n</main><script src="../assets/chatbot-config.js" defer></script><script src="../assets/chatbot/innovae-chat.js" data-conocimiento="conocimiento.json" defer></script></body></html>\n`);
  // Conserva los antiguos enlaces de fragmento; las tarjetas nuevas usan enlaces HTML rastreables.
  const card = new RegExp(`<div ((?:class="(?:svc-card|team-card)[^>]+)) onclick="location.hash='#${id}'" onkeydown="[^"]*">([\\s\\S]*?)\\n        <\\/div>`);
  index = index.replace(card, (_, attrs, contents) => `<a ${attrs.replace(/ role="link" tabindex="0"/, '')} href="${file}">${contents}\n        </a>`);
  index = index.replace(original, original.replace(/<h1 class="td-title">([\s\S]*?)<\/h1>/, '<h2 class="td-title">$1</h2>'));
  pages.push(file);
}
assert.equal(pages.length, 29, '25 tratamientos y 4 perfiles');
write('assets/fichas.css', styles + '\n/* Las fichas independientes usan el flujo normal del documento. */\nmain { background: var(--cream); min-height: 100vh; }\n.td-block h2 { font-family: "Cormorant Garamond", serif; font-size: 1.6rem; font-weight: 400; margin-bottom: 12px; }\n');
if (!index.includes('/* ENLACES DE FICHAS */')) index = index.replace('</style>', '/* ENLACES DE FICHAS */\n    a.svc-card, a.team-card { display: block; color: inherit; text-decoration: none; }\n    a.svc-card:focus-visible, a.team-card:focus-visible { outline: 3px solid var(--gold); outline-offset: 4px; }\n  </style>');
if (!index.includes('// Tratamiento elegido desde una ficha independiente.')) index = index.replace('    // Detalles de servicios', `    // Tratamiento elegido desde una ficha independiente.
    document.addEventListener('DOMContentLoaded', function () {
      const nombre = new URLSearchParams(location.search).get('tratamiento');
      if (nombre && Array.from(document.getElementById('r-tratamiento').options).some(o => o.value === nombre)) preselectTratamiento(nombre);
    });

    // Detalles de servicios`);
write('index.html', index);
const products = JSON.parse(fs.readFileSync(path.join(root, 'productos/datos-productos.json'), 'utf8'));
const urls = ['', ...products.map(p => 'productos/' + p.id + '.html'), ...pages];
write('sitemap.xml', `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map(file => `  <url><loc>${escape(base + file)}</loc></url>`).join('\n')}\n</urlset>\n`);
write('robots.txt', `User-agent: *\nAllow: /\n\nSitemap: ${base}sitemap.xml\n`);
// Los borradores y la demo también tienen identidad propia, pero no se indexan como páginas oficiales.
for (const [file, title, description] of [
  ['borrador index servicios.html', 'Borrador de servicios | Clínica Innovae', 'Borrador del diseño de servicios, equipo y reservas de Clínica Innovae. Página de referencia para el desarrollo de la web.'],
  ['boceto-1/index.html', 'Boceto 1 de la web | Clínica Innovae', 'Primera propuesta de diseño para la web de Clínica Innovae: presentación, tratamientos y contacto.'],
  ['boceto-2/index.html', 'Boceto 2 de la web | Clínica Innovae', 'Segunda propuesta de diseño para la web de Clínica Innovae: medicina estética, tratamientos y solicitud de cita.'],
  ['chatbot/widget/demo.html', 'Demostración del chat | Clínica Innovae', 'Página de pruebas del asistente de Clínica Innovae para consultar información sobre tratamientos, productos y contacto.'],
]) {
  let html = fs.readFileSync(path.join(root, file), 'utf8');
  html = html.replace(/<title>[\s\S]*?<\/title>/, `<title>${escape(title)}</title>`)
    .replace(/\s*<meta name="(?:description|robots)"[^>]*>/g, '');
  html = html.replace('</head>', `<meta name="description" content="${escape(description)}">\n<meta name="robots" content="noindex, follow">\n</head>`);
  write(file, html);
}
console.log(`SEO: ${urls.length} páginas en el sitemap, con títulos y descripciones individuales; 4 borradores excluidos de indexación.`);

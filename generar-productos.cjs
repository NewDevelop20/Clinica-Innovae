// Regenera el catálogo y las páginas desde las fichas. Ejecutar: node generar-productos.cjs
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = __dirname;
const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inline = s => escape(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>').replace(/\*([^*]+)\*/g, '<em>$1</em>');
const slug = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const source = fs.readFileSync(path.join(root, 'fichas-productos-innovae.md'), 'utf8');
const products = [...source.matchAll(/^## \d+\. (.+)\r?\n([\s\S]*?)(?=^## \d+\.|$(?![\s\S]))/gm)].map(match => {
  const name = match[1].trim();
  const body = match[2];
  const fields = Object.fromEntries([...body.matchAll(/^\| ([^|]+) \| ([^|]+) \|\r?$/gm)].map(m => [m[1].trim(), m[2].trim()]).filter(([key]) => key !== 'Campo'));
  const sections = [...body.matchAll(/^\*\*([^*]+)\*\*([^]*?)(?=^\*\*|^---|^> |$(?![\s\S]))/gm)].map(m => ({title: m[1].replace(/:$/, ''), text: m[2].replace(/^:\s*/, '').trim()}));
  const get = title => sections.find(s => s.title === title)?.text || '';
  return {id: slug(name), name, fields, sections: sections.filter(s => !['Descripción corta', 'Galería'].includes(s.title)), summary: get('Descripción corta'), images: [], usageImages: [], sourceImages: get('Galería').split(/\r?\n/).filter(s => s.startsWith('- ')).map(s => s.slice(2))};
});
assert.equal(products.length, 11, 'Deben existir las once fichas');
assert.equal(new Set(products.map(p => p.id)).size, 11);
const productDir = path.join(root, 'productos');
fs.mkdirSync(productDir, {recursive: true});
const dataFile = path.join(productDir, 'datos-productos.json');
const previous = fs.existsSync(dataFile) ? JSON.parse(fs.readFileSync(dataFile, 'utf8')) : [];
for (const p of products) {
  const saved = previous.find(item => item.id === p.id);
  if (saved) {
    p.images = (saved.images || []).filter(Boolean);
    p.usageImages = (saved.usageImages || []).filter(Boolean);
  }
}
fs.writeFileSync(path.join(productDir, 'datos-productos.json'), JSON.stringify(products, null, 2) + '\n');
const renderProduct = require('./plantilla-producto.cjs');
for (const p of products) {
  const html = renderProduct(p);
  fs.writeFileSync(path.join(productDir, p.id + '.html'), html);
  assert.equal((html.match(/data-image-slot=/g) || []).length, p.images.length);
  assert.equal((html.match(/class="usage-image"/g) || []).length, p.usageImages.length);
  assert(html.includes(escape(p.summary)));
  for (const id of ['modo-de-uso', 'rutina', 'resultados']) assert(html.includes(`id="${id}"`));
  for (const section of p.sections) {
    const plain = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    const bits = section.text.split(/\r?\n|(?<=\.)\s+(?=[A-ZÁÉÍÓÚÜ*])|\d\)\s*/).filter(Boolean);
    for (const bit of bits) assert(plain.includes(escape(bit.replace(/^- /, '').replace(/\*/g, '')).replace(/\s+/g, ' ').trim()), `Texto ausente: ${p.name} / ${section.title}`);
  }
}
let index = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const cards = products.map(p => `<a class="shop-card reveal" href="productos/${p.id}.html">
  <div class="shop-img shop-placeholder">${p.images[0] ? `<img src="${escape(p.images[0].replace(/^\.\.\//, ''))}" alt="${escape(p.name)}" loading="lazy">` : '<span>Imagen próximamente</span>'}</div>
  <div class="shop-body"><span class="shop-line">${escape(p.fields.Marca)} · ${escape(p.fields['Línea'])}</span>
  <h3 class="shop-name">${escape(p.name)}</h3><p class="shop-desc">${escape(p.summary)}</p>
  <div class="shop-foot"><span class="shop-btn">Ver ficha <span aria-hidden="true">↗</span></span></div></div></a>`).join('\n');
const start = index.indexOf('  <!-- TIENDA -->');
const end = index.indexOf('  <!-- CONTACTO -->', start);
assert(start > 0 && end > start);
const shop = `  <!-- TIENDA -->
  <section id="tienda"><div class="container"><div class="shop-header">
  <span class="label reveal">Nuestro catálogo</span><h2 class="title reveal">Cosmética profesional<br><em>para llevar a casa</em></h2>
  <div class="rule reveal"></div><p class="body-text reveal">Descubre nuestra selección de productos para el cuidado diario de tu piel. Consulta cada ficha para conocer sus beneficios y cómo utilizarlos.</p>
  <span class="shop-brand reveal"><strong>Germaine de Capuccini</strong> · <strong>mesoestetic</strong></span></div>
  <div class="shop-grid">${cards}</div>
  <p class="shop-note reveal">Para consultar precios, disponibilidad o realizar tu pedido, contáctanos y te asesoramos personalmente.</p>
  </div></section>\n\n`;
index = index.slice(0, start) + shop + index.slice(end);
if (!index.includes('/* PRODUCT LINKS */')) index = index.replace('    /* ── CONTACT ── */', `    /* PRODUCT LINKS */
    a.shop-card { color: inherit; text-decoration: none; }
    a.shop-card:focus-visible { outline: 3px solid var(--gold-dark); outline-offset: 5px; }
    .shop-placeholder { display: grid; place-items: center; }
    .shop-placeholder span { font-size: .7rem; color: var(--text-mid); position: relative; z-index: 1; }
    /* ── CONTACT ── */`);
fs.writeFileSync(path.join(root, 'index.html'), index);
assert.equal((index.match(/href="productos\//g) || []).length, 11);
const pages = [path.join(root, 'index.html'), ...products.map(p => path.join(productDir, p.id + '.html'))];
for (const file of pages) {
  const html = fs.readFileSync(file, 'utf8');
  for (const match of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
    const url = match[1];
    if (/^(https?:|mailto:|tel:)/.test(url)) continue;
    const [relative, anchor] = url.split('#');
    const target = relative ? path.resolve(path.dirname(file), relative) : file;
    assert(fs.existsSync(target), `Recurso inexistente: ${url}`);
    if (anchor) assert(fs.readFileSync(target, 'utf8').includes(`id="${anchor}"`), `Anclaje inexistente: ${url}`);
  }
}
console.log(`Verificado: 11 enlaces, 11 fichas completas, ${products.reduce((n, p) => n + p.images.length, 0)} imágenes de producto y ${products.reduce((n, p) => n + p.usageImages.length, 0)} imágenes de uso.`);
console.log('Verificados los recursos locales y los enlaces de vuelta al catálogo en los 12 HTML.');

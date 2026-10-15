"""Verifica el HTML estático que los buscadores reciben, sin ejecutar JavaScript."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://newdevelop20.github.io/Clinica-Innovae/'

class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.titles, self.headings, self.metas, self.canonicals, self.links = [], [], {}, [], []
        self.capture = None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('title', 'h1'):
            self.capture = tag
            (self.titles if tag == 'title' else self.headings).append('')
        if tag == 'meta':
            self.metas.setdefault(a.get('name', a.get('property')), []).append(a.get('content', ''))
        if tag == 'link' and a.get('rel') == 'canonical':
            self.canonicals.append(a['href'])
        if tag in ('a', 'link', 'script', 'img'):
            url = a.get('href', a.get('src'))
            if url:
                self.links.append(url)
    def handle_data(self, data):
        if self.capture:
            values = self.titles if self.capture == 'title' else self.headings
            values[-1] += data
    def handle_endtag(self, tag):
        if tag == self.capture:
            self.capture = None

urls = [e.text for e in ET.parse(ROOT / 'sitemap.xml').findall('.//{*}loc')]
assert len(urls) == len(set(urls)) == 44
seen_titles, seen_descriptions = set(), set()
for url in urls:
    assert url.startswith(BASE)
    file = ROOT / (url[len(BASE):] or 'index.html')
    doc = Document(file.read_text())
    assert len(doc.titles) == len(doc.headings) == 1, file
    title = doc.titles[0].strip()
    description = doc.metas.get('description', [])
    assert len(description) == 1 and len(description[0]) >= 45, file
    assert title and title not in seen_titles, (file, title)
    assert description[0] not in seen_descriptions, (file, description)
    seen_titles.add(title)
    seen_descriptions.add(description[0])
    assert doc.canonicals == [url], file
    assert doc.metas.get('og:title') == doc.metas.get('twitter:title') == [title], file
    assert doc.metas.get('og:description') == doc.metas.get('twitter:description') == description, file
    assert doc.metas.get('og:url') == [url], file
    assert 'noindex' not in ','.join(doc.metas.get('robots', [])), file
    for link in doc.links:
        parts = urlsplit(link)
        if parts.scheme or parts.netloc:
            continue
        target = (file.parent / unquote(parts.path)).resolve() if parts.path else file
        if target.is_dir():
            target = target / 'index.html'
        assert target.is_file(), (file, link)
        if parts.fragment:
            assert f'id="{unquote(parts.fragment)}"' in target.read_text(), (file, link)
for file in ['borrador index servicios.html', 'boceto-1/index.html', 'boceto-2/index.html', 'chatbot/widget/demo.html']:
    doc = Document((ROOT / file).read_text())
    assert len(doc.titles) == len(doc.metas['description']) == 1
    assert doc.metas['robots'] == ['noindex, follow']
home = Document((ROOT / 'index.html').read_text())
for url in urls[1:]:
    assert url[len(BASE):] in home.links, url
assert f'Sitemap: {BASE}sitemap.xml' in (ROOT / 'robots.txt').read_text()
print('SEO verificado: 44 páginas únicas, metadatos, H1, sitemap y enlaces; 4 borradores noindex.')

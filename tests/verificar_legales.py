"""Prueba enlaces legales y consentimiento de Maps sin llamar a Google ni crear reservas."""
from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
import subprocess, time, shutil

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8773/'
server = subprocess.Popen(['python3', '-m', 'http.server', '8773', '--bind', '127.0.0.1', '--directory', str(ROOT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        try:
            urlopen(BASE).close()
            break
        except OSError:
            time.sleep(.1)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 900})
            requests, errors = [], []
            context.route('https://**/*', lambda route: route.abort())
            page = context.new_page()
            page.on('request', lambda request: requests.append(request.url))
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE, wait_until='networkidle')
            frame = page.locator('#contact-map-frame')
            assert frame.get_attribute('src') is None
            assert not any('maps.google.com' in url for url in requests)
            expect(page.locator('#r-rgpd + label a')).to_have_attribute('href', 'politica-privacidad.html')
            assert page.locator('footer nav.legal-links a').count() == 3
            page.locator('#load-map').click()
            expect(frame).to_be_visible()
            assert 'maps.google.com' in frame.get_attribute('src')
            assert page.evaluate("localStorage.getItem('innovae_mapa')") == 'aceptado'
            page.reload(wait_until='networkidle')
            expect(frame).to_be_visible()
            # Revocación en otra pestaña: el mapa abierto debe desaparecer inmediatamente.
            policy = context.new_page()
            policy.goto(BASE + 'politica-cookies.html')
            policy.locator('#retirar').click()
            expect(policy.locator('#estado')).to_contain_text('Consentimiento retirado')
            expect(frame).to_be_hidden()
            assert frame.get_attribute('src') is None
            requests.clear()
            page.reload(wait_until='networkidle')
            assert not any('maps.google.com' in url for url in requests)
            # Documentos y navegación legibles, sin desbordamiento en móvil.
            for file in ('aviso-legal.html', 'politica-privacidad.html', 'politica-cookies.html'):
                page.goto(BASE + file, wait_until='networkidle')
                expect(page.locator('h1')).to_be_visible()
                assert page.locator('body').evaluate('(e) => e.scrollWidth') <= width, file
                assert page.locator('footer a').count() == 3
            for file in ('productos/crema-pro-colageno.html', 'tratamientos/arrugas.html', 'equipo/jimenez.html'):
                page.goto(BASE + file, wait_until='networkidle')
                assert page.locator('footer .legal-links a').count() == 3
            assert not errors, errors
            context.close()
            print(f'PASS {width}px: documentos, enlaces legales, mapa bloqueado hasta consentimiento, persistencia y retirada entre pestañas.')
        browser.close()
finally:
    server.terminate()
    server.wait()

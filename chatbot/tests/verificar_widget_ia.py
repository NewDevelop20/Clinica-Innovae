"""Verifica el widget en modo IA con HTTP simulado; no llama a Anthropic ni Google."""
from pathlib import Path
from urllib.request import urlopen
import subprocess, time, shutil, json
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
base = 'http://127.0.0.1:8776/'
server = subprocess.Popen(['python3', '-m', 'http.server', '8776', '--bind', '127.0.0.1', '--directory', str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(30):
        try:
            urlopen(base).close()
            break
        except OSError:
            time.sleep(.1)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), args=['--no-sandbox'])
        for width in (1440, 390):
            page = browser.new_page(viewport={'width': width, 'height': 900})
            errors, calls = [], []
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.route('https://**/*', lambda route: route.abort())
            def responder(route):
                if route.request.method == 'OPTIONS':
                    route.fulfill(status=204, headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type','Access-Control-Allow-Methods':'POST'})
                    return
                calls.append(json.loads(route.request.post_data))
                route.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'respuesta':'Solicitud de prueba #AB12CD34, pendiente de confirmación por la clínica.'}))
            page.route('https://chatbot.test/api/chat', responder)
            page.add_init_script("Object.defineProperty(window,'INNOVAE_CHAT_CONFIG',{get:()=>({api:'https://chatbot.test'}),set:()=>{}})")
            page.goto(base, wait_until='networkidle')
            widget = page.locator('#innovae-chat')
            widget.locator('.lanzador').click()
            expect(widget.locator('.cab p')).to_contain_text('con IA')
            welcome = widget.locator('.m.bot').first
            expect(welcome).to_contain_text('inteligencia artificial')
            expect(welcome).to_contain_text('No doy consejo médico')
            expect(welcome).to_contain_text('hablar con una persona')
            expect(welcome.locator('a')).to_have_attribute('href','https://newdevelop20.github.io/Clinica-Innovae/politica-privacidad.html')
            expect(widget.locator('.pie a').first).to_have_attribute('href', 'tel:+34661734870')
            expect(widget.locator('.pie a').last).to_have_attribute('href','https://newdevelop20.github.io/Clinica-Innovae/politica-privacidad.html')
            widget.locator('textarea').fill('Sí, confirmo la solicitud de prueba')
            widget.locator('.enviar').click()
            expect(widget.locator('.m.bot').last).to_contain_text('pendiente de confirmación')
            assert len(calls) == 1 and calls[0]['mensaje'] == 'Sí, confirmo la solicitud de prueba'
            assert calls[0]['sesion_id']
            page.reload(wait_until='networkidle')
            expect(widget.locator('.m.bot').first).to_contain_text('inteligencia artificial')
            expect(widget.locator('.m.bot').last).to_contain_text('AB12CD34')
            widget.locator('.reiniciar').click()
            expect(widget.locator('.m.bot')).to_have_count(1)
            expect(widget.locator('.m.bot')).to_contain_text('No doy consejo médico')
            assert not errors, errors
            page.screenshot(path=f'/tmp/innovae-widget-ia-{width}.png')
            page.close()
            print(f'PASS {width}px: aviso IA, límite médico, persona, privacidad y HTTP/historial simulados.')
        browser.close()
finally:
    server.terminate()
    server.wait()

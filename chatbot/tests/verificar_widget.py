from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright, expect
import subprocess,time,json,shutil
root=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1','--directory',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(30):
  try:urlopen('http://127.0.0.1:8765/index.html').close();break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  datos=json.loads((root/'assets/chatbot/conocimiento.json').read_text())
  for width in [1440,390]:
   page=browser.new_page(viewport={'width':width,'height':850});errors=[];requests=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
   page.route('https://**/*',lambda r:r.abort())
   page.goto('http://127.0.0.1:8765/index.html',wait_until='networkidle')
   widget=page.locator('#innovae-chat');widget.locator('.lanzador').click();expect(widget.locator('.panel')).to_be_visible()
   expect(widget.locator('.cab p')).to_contain_text('sin IA')
   def pregunta(q, esperado):
    widget.locator('textarea').fill(q);widget.locator('.enviar').click()
    expect(widget.locator('.enviar')).to_be_enabled(timeout=10000)
    expect(widget.locator('.m.bot').last).to_contain_text(esperado)
    return widget.locator('.m.bot').last.inner_text()
   pregunta('¿Cuál es el horario y la ubicación?','16:30–20:30')
   pregunta('¿Dónde estáis?','Ramón y Cajal')
   pregunta('¿Cuánto cuesta Dermapen?','precios no están publicados')
   pregunta('Quiero reservar una cita','No puedo consultar la agenda')
   pregunta('Estoy embarazada, ¿puedo usar NIGHT?','profesional')
   pregunta('No puedo respirar','112')
   pregunta('¿Qué tratamientos hacéis?','Limpieza Facial')
   pregunta('¿Qué productos vendéis?','NIGHT')
   for a in datos['articulos']:
    respuesta=pregunta('Información sobre '+a['nombre'],a['nombre'])
    assert a['texto'].split('\n')[0] in respuesta,(a['nombre'],respuesta)
   respuesta=pregunta('<img src=x onerror=alert(1)> ¿Aparcamiento gratis?','No encuentro una respuesta')
   assert widget.locator('.lista img').count()==0
   assert not any('/api/chat' in u for u in requests),requests
   widget.locator('.reiniciar').click();assert widget.locator('.m.yo').count()==0
   pregunta('Háblame de Radiofrecuencia','Calor controlado')
   page.reload(wait_until='networkidle');expect(widget.locator('.m.bot').last).to_contain_text('Calor controlado')
   panel=widget.locator('.panel').bounding_box();assert panel['x']>=0 and panel['x']+panel['width']<=width
   page.screenshot(path=f'/tmp/innovae-chat-{width}.png')
   widget.locator('textarea').press('Escape');expect(widget.locator('.panel')).to_be_hidden()
   assert not errors,errors
   print(f'PASS {width}px: 37 consultas, preguntas frecuentes, reservas desactivadas, límites médicos, persistencia, reinicio y teclado.',flush=True)
   page.close()
  # Las 11 fichas usan recursos relativos correctos y conservan las galerías.
  page=browser.new_page();page.route('https://**/*',lambda r:r.abort())
  for a in datos['articulos']:
   if a['tipo']!='producto':continue
   name=a['url'].split('/')[-1];page.goto('http://127.0.0.1:8765/productos/'+name,wait_until='domcontentloaded')
   expect(page.locator('#innovae-chat .lanzador')).to_be_visible()
   assert page.locator('[data-image-slot]').count()>0
  print('PASS widget en las 11 fichas de producto.',flush=True)
  browser.close()
finally:server.terminate();server.wait()

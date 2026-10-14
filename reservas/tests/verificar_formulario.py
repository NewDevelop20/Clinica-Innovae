from pathlib import Path
from urllib.request import urlopen
from playwright.sync_api import sync_playwright,expect
from urllib.parse import urlparse,parse_qs
from datetime import datetime,timedelta
import json,subprocess,time,shutil
root=Path(__file__).resolve().parents[2]
d=datetime.now().date()+timedelta(days=3)
while d.weekday()!=0:d+=timedelta(days=1)
dia=d.isoformat()
server=subprocess.Popen(['python3','-m','http.server','8765','--bind','127.0.0.1','--directory',str(root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
 for _ in range(30):
  try:urlopen('http://127.0.0.1:8765/index.html').close();break
  except OSError:time.sleep(.1)
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
  for width in [1440,390]:
   page=browser.new_page(viewport={'width':width,'height':950});errors=[];posts=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.route('https://**/*',lambda r:r.abort())
   page.add_init_script("Object.defineProperty(window,'INNOVAE_RESERVAS_CONFIG',{get:()=>({endpoint:'',modoPruebas:true}),set:()=>{}})")
   page.goto('http://127.0.0.1:8765/index.html#reservas',wait_until='networkidle')
   expect(page.locator('#bookingTestNotice')).to_contain_text('no reserve una cita real');expect(page.locator('#bookingStatus')).to_contain_text('no está conectada');assert page.locator('#r-submit').is_disabled();assert not page.locator('#bookingConfirm').is_visible()
   page.close();page=browser.new_page(viewport={'width':width,'height':950});page.on('pageerror',lambda e:errors.append(str(e)))
   page.route('https://**/*',lambda r:r.abort())
   resultado={'ok':False,'error':'Esa hora ya está completa.'}
   def script(route):
    q=parse_qs(urlparse(route.request.url).query)
    if route.request.method=='GET':
     callback=q['callback'][0];res={'ok':True,'bloqueadas':['10:00']}
     route.fulfill(status=200,content_type='application/javascript',body=callback+'('+json.dumps(res)+');')
    else:
     datos={k:v[0] for k,v in parse_qs(route.request.post_data,keep_blank_values=True).items()};posts.append(datos)
     msg={'tipo':'innovae-reserva','requestId':datos['requestId'],'resultado':resultado.copy()}
     # Google sirve la página HTML a través de un iframe interior en googleusercontent.
     page_id=str(len(posts));nested='https://n-test-script.googleusercontent.com/result?request='+page_id
     route.fulfill(status=200,content_type='text/html',body='<iframe src="'+nested+'"></iframe>')
     mensajes[page_id]=msg
   mensajes={}
   def resultado_google(route):
    msg=mensajes[parse_qs(urlparse(route.request.url).query)['request'][0]]
    route.fulfill(status=200,content_type='text/html',body='<script>window.top.postMessage('+json.dumps(msg)+',"http://127.0.0.1:8765")</script>')
   page.route('https://script.google.com/macros/s/TEST/exec**',script);page.route('https://n-test-script.googleusercontent.com/**',resultado_google)
   page.add_init_script("Object.defineProperty(window,'INNOVAE_RESERVAS_CONFIG',{get:()=>({endpoint:'https://script.google.com/macros/s/TEST/exec'}),set:()=>{}})")
   page.goto('http://127.0.0.1:8765/index.html#reservas',wait_until='networkidle')
   page.locator('#r-nombre').fill('Ana Prueba');page.locator('#r-telefono').fill('600123456');page.locator('#r-email').fill('ana@example.com');page.locator('input[name="primera"][value="No"]').check();page.locator('#r-tratamiento').select_option(label='Limpieza Facial');page.locator('#r-fecha').fill(dia);page.locator('#r-fecha').dispatch_event('change')
   expect(page.locator('#r-submit')).to_be_enabled();assert page.locator('#r-hora option[value="10:00"]').count()==0;assert page.locator('#r-hora option[value="13:00"]').count()==0;assert page.locator('#r-hora option[value="16:30"]').count()==1
   page.locator('#r-hora').select_option('10:30');page.locator('#r-notas').fill('Prueba sin clientes');page.locator('#r-rgpd').check()
   # Mensajes inventados con origen local no deben producir una confirmación.
   page.evaluate("window.postMessage({tipo:'innovae-reserva',requestId:'inventado',resultado:{ok:true,id:'AB12CD34'}},'*')")
   assert not page.locator('#bookingConfirm').is_visible()
   page.locator('#r-submit').click();expect(page.locator('#bookingStatus')).to_contain_text('ya está completa');assert not page.locator('#bookingConfirm').is_visible();expect(page.locator('#r-submit')).to_be_enabled()
   resultado.update({'ok':True,'id':'AB12CD34','estado':'PENDIENTE','aviso_enviado':True});page.locator('#r-submit').click();expect(page.locator('#bookingConfirm')).to_be_visible();expect(page.locator('#bc-detail')).to_contain_text('AB12CD34');expect(page.locator('#bc-note')).to_contain_text('pendiente')
   assert posts[0]['primeraVisita']=='false' and posts[0]['comentarios']=='Prueba sin clientes';assert 'primera' not in posts[0] and 'notas' not in posts[0];assert posts[0]['requestId']==posts[1]['requestId']
   assert not errors,errors
   print(f'PASS {width}px: sin endpoint no hay falso éxito; horas reales simuladas, error, reintento idempotente, iframe anidado, campos y código de reserva.',flush=True)
   page.close()
  browser.close()
finally:server.terminate();server.wait()

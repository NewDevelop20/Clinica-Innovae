"""Publica el widget y un catálogo de consulta sin claves ni notas internas."""
from pathlib import Path
import json
import re
import shutil

RAIZ = Path(__file__).resolve().parent
WEB = RAIZ.parent

def exportar():
    salida = WEB / 'assets' / 'chatbot'
    salida.mkdir(parents=True, exist_ok=True)
    tratamientos = re.sub(r'<!--.*?-->', '', (RAIZ / 'conocimiento/tratamientos.md').read_text(), flags=re.S)
    articulos = []
    categoria = ''
    for parte in re.split(r'(?m)^(?=## )', tratamientos):
        m = re.match(r'## (.+)', parte)
        if m:
            categoria = m[1]
        for m in re.finditer(r'(?m)^### (.+)\n([\s\S]*?)(?=^### |\Z)', parte):
            articulos.append({'tipo': 'tratamiento', 'nombre': m[1], 'categoria': categoria,
                              'texto': m[2].strip()})
    productos = json.loads((WEB / 'productos/datos-productos.json').read_text())
    for p in productos:
        descripcion = next((s['text'] for s in p['sections'] if s['title'] == 'Descripción'), p['summary'])
        articulos.append({'tipo': 'producto', 'nombre': p['name'], 'alias': p['id'].replace('-', ' '),
                          'texto': p['summary'] + '\n\n' + descripcion,
                          'url': 'https://newdevelop20.github.io/Clinica-Innovae/productos/' + p['id'] + '.html'})
    datos = {'faq': {
        'horario': 'Lunes a viernes: 10:00–13:30 y 16:30–20:30. Sábado: 10:30–13:00. Domingo: cerrado. En festivos, confirme el horario con la clínica.',
        'direccion': 'Av. Ramón y Cajal, 10 · 23400 Úbeda, Jaén. Cómo llegar: https://www.google.com/maps/search/?api=1&query=Cl%C3%ADnica+Innovae+%C3%9Abeda',
        'precios': 'Los precios no están publicados. Dependen de la valoración y del caso. Puede consultar precio y disponibilidad con la clínica.',
        'reservas': 'Las reservas automáticas del chat aún no están activadas. No puedo consultar la agenda ni registrar o confirmar una cita. Para pedir, cambiar o cancelar una cita, contacte con la clínica.',
        'equipo': 'El Dr. Francisco Javier Romero Conesa es el director médico, especialista en Medicina Estética y Flebología. Los tratamientos de Medicina Estética requieren valoración médica previa.',
        'tienda': 'Disponemos de cosmética Germaine de Capuccini y mesoestetic para recogida en la clínica. Consulte precio y disponibilidad con el equipo.'
    }, 'articulos': articulos}
    (salida / 'conocimiento.json').write_text(json.dumps(datos, ensure_ascii=False, indent=2) + '\n')
    shutil.copyfile(RAIZ / 'widget/innovae-chat.js', salida / 'innovae-chat.js')
    print(f'Publicado widget y conocimiento: {len(articulos)} artículos (27 opciones de tratamiento y 11 productos).')

if __name__ == '__main__':
    exportar()

# Páginas y metadatos

La portada, los 11 productos, los 25 tratamientos y los 4 perfiles y los 3 documentos legales tienen una URL canónica, un título y una descripción únicos. Los enlaces de las tarjetas son enlaces HTML y el contenido de las fichas se entrega sin depender de JavaScript. `sitemap.xml` enumera las 44 páginas y `robots.txt` indica dónde encontrarlo. Los bocetos y la demo conservan sus archivos, con `noindex, follow` para evitar que compitan con las páginas oficiales.

Para actualizar y comprobar las páginas, desde la raíz:

```sh
node generar-productos.cjs
node generar-seo.cjs
python tests/verificar_seo.py
```

- Productos: editar `fichas-productos-innovae.md`; sus descripciones cortas se usan en los metadatos. `plantilla-producto.cjs` usa el generador compartido `seo.cjs`.
- Tratamientos y equipo: editar los bloques `treatment-detail` del `index.html`. `generar-seo.cjs` reutiliza ese contenido y define las descripciones de cada tratamiento; los perfiles usan su nombre y especialidad. Los antiguos enlaces con fragmento siguen funcionando.
- Portada: título y descripción en `generar-seo.cjs`.
- Dominio: actualizar `base` en `seo.cjs` y regenerar si cambia la dirección pública.

La comprobación valida unicidad, metadatos sociales, un H1 por página, enlaces locales y sitemap. La generación se ejecuta también en GitHub Actions para detectar archivos generados desactualizados. Google decide cuándo rastrear y qué texto mostrar en los resultados; estos cambios no garantizan indexación inmediata.

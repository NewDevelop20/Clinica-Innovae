# Catálogo y fichas de productos

El catálogo de `index.html` enlaza a once páginas en `productos/`, generadas con los textos de `fichas-productos-innovae.md`. Las tarjetas son enlaces completos, utilizables con ratón y teclado. Las fichas cuentan con enlaces para volver al catálogo y consultar precio y disponibilidad por email.

El nuevo diseño sigue la distribución de la ficha de referencia: imagen principal y cuatro miniaturas a la izquierda, información a la derecha y tres secciones inferiores: Modo de uso, Rutina completa y Resultados. Mantiene la paleta de Innovae. Los ingredientes o el contenido del set se conservan en desplegables dentro de la información principal.

`plantilla-producto.cjs` define la estructura. `productos/producto-v2.css` contiene los estilos adaptados a escritorio y móvil. `productos/producto.js` controla las miniaturas, con navegación por clic, flechas, Inicio y Fin. El resto del contenido es HTML estático. Los resultados muestran los beneficios del documento, sin porcentajes clínicos añadidos.

Cada ficha contiene cuatro espacios vacíos para fotografías. No se han añadido precios porque no aparecen en el documento.

## Añadir imágenes

1. Guarda las fotografías en `assets/productos/`.
2. En `productos/datos-productos.json`, busca el producto y rellena sus cuatro entradas `images` con rutas relativas a la ficha, por ejemplo `../assets/productos/gdc-srns-night-1.jpg`. Las entradas vacías mantienen el espacio reservado. La primera imagen también se utiliza en la tarjeta del catálogo.
3. Ejecuta `node generar-productos.cjs` desde la carpeta del proyecto para actualizar las páginas. El generador conserva las imágenes configuradas. `sourceImages` conserva las URLs de referencia del documento, sin cargarlas en la web.

Para actualizar textos, edita `fichas-productos-innovae.md` y ejecuta el mismo comando.

## Publicar

Sube `index.html`, `productos/` y `assets/` conservando sus rutas relativas. No basta con reemplazar solo `index.html`.

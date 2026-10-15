# Tipografías locales

Cormorant Garamond (pesos 300–700) y Montserrat (100–900), en redonda y cursiva.
Se sirven archivos WOFF2 variables con los subconjuntos latin y latin-ext para
cubrir el español y el resto de caracteres latinos. `fonts.css` usa `font-display: swap`.

Los archivos se han descargado del servicio oficial Google Fonts y se distribuyen
sin modificar bajo SIL Open Font License 1.1. Las dos licencias están incluidas.
`origenes.json` contiene los enlaces de procedencia y los hashes SHA-256.
La web entrega las fuentes desde el mismo sitio que el HTML: no consulta a Google
Fonts ni a fonts.gstatic.com durante la navegación.

Las páginas usan `assets/fonts/fonts.css` con la ruta relativa correspondiente.
Al regenerar productos o fichas se conserva esta referencia local.

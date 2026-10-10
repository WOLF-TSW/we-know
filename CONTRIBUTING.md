# Guía de contribución

## Pasos

1. Haz un *fork* y crea una rama: `anotar/nombre-apellido`.
2. Copia `personas/_plantilla.yml` → `personas/nombre-apellido.yml` (minúsculas, sin acentos, con guiones).
3. Completa **cada mención** con documento, página, URL oficial, cita y categoría.
4. Ejecuta el validador:
   ```bash
   pip install -r requirements.txt
   python scripts/validar_entradas.py personas
   ```
5. Abre la PR y completa la lista de comprobación de la plantilla.

## Qué revisan los revisores

- La cita existe en la página indicada (el CI lo comprueba si el índice está disponible; los revisores lo confirman a mano).
- El enlace es de una fuente oficial.
- El contexto es neutral y está atribuido.
- No hay datos de víctimas ni datos personales.

## Categorías de mención

`registro_de_vuelos` · `correspondencia` · `testimonio` · `agenda_de_contactos` ·
`mencion_pasajera` · `documento_financiero` · `denuncia_no_verificada` · `otro`

## Verificación

- `documentada`: la mención aparece tal cual en un documento oficial.
- `denuncia_no_verificada`: es una afirmación de un tercero sin corroborar.
- `ilegible_ocr`: el OCR es dudoso; un revisor debe confirmar con el original.

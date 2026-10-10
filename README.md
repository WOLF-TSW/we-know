# Archivos Wiki: qué dicen los documentos

App (web instalable y APK) que busca **en qué documentos públicos del caso Epstein se menciona a una persona y en qué contexto**, con una wiki comunitaria revisada por pares.

> **Aparecer en un documento NO implica culpabilidad ni participación en delito alguno.**
> Muchas menciones son de abogados, periodistas, empleados, testigos, víctimas o contactos.
> Este proyecto describe *qué dice cada documento*, nunca *qué hizo una persona*.

## Arquitectura (sin servidor propio)

```
Repos de GitHub con OCR  ──(GitHub Action semanal)──►  índice estático  ──►  GitHub Pages ◄── App web / APK
personas/*.yml (wiki, PRs revisadas) ──(validar + compilar)──────────────────────────┘
```

| Capa | Dónde vive | Quién la mantiene |
|---|---|---|
| Texto OCR de los documentos | Repos comunitarios de GitHub (`build/fuentes.json`) | Terceros |
| Índice de búsqueda (JSON estático por fragmentos) | GitHub Pages (`/data`) | Automático |
| Anotaciones con contexto, categoría y atribución | `personas/*.yml` | Comunidad, con revisión |
| App | `app/` (PWA) y APK vía Capacitor | Mantenedores |

La app solo descarga los fragmentos del índice que necesita para cada búsqueda; no hay base de datos ni servidor.

## Puesta en marcha

1. Sube este repo a GitHub.
2. **Settings → Pages → Source: GitHub Actions.**
3. Ejecuta **Actions → Publicar app e índice → Run workflow**. Al terminar tendrás la app en `https://USUARIO.github.io/REPO/` (instalable desde Chrome: *Añadir a pantalla de inicio*).
4. **APK:** ejecuta **Actions → Compilar APK → Run workflow** y descarga `archivos-wiki-apk` desde *Artifacts*. Con una etiqueta `v1.0.0` el APK se adjunta a la release.
5. Configura la protección de `main` según [`docs/CONFIGURAR_GITHUB.md`](docs/CONFIGURAR_GITHUB.md).

> El APK de `assembleDebug` está firmado con clave de depuración: sirve para instalar directamente (activa "orígenes desconocidos"). Para Google Play necesitas firmar con tu propio keystore.

## Fuentes de datos

`build/fuentes.json` lista los repos de GitHub de los que se lee el texto OCR. El extractor reconoce varios formatos JSON de OCR y `.txt/.md`. **Antes del primer despliegue, revisa que `ruta` apunte a la carpeta correcta del repo fuente** y que el índice salga con documentos (el flujo falla si no indexa ninguno).

## Contribuir a la wiki

1. Lee [`POLITICA_CONTENIDO.md`](POLITICA_CONTENIDO.md) (obligatorio).
2. Copia `personas/_plantilla.yml` a `personas/nombre-apellido.yml`.
3. Valida: `python scripts/validar_entradas.py personas`
4. Abre una Pull Request: requiere **2 aprobaciones**. Guía completa en [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Retiros y correcciones

- Cualquier persona puede abrir un issue con la plantilla **Solicitud de corrección o retiro** (la app incluye un enlace en cada resultado).
- `build/retirados.txt` permite excluir documentos completos o páginas que contengan una frase. Úsalo para proteger identidades de víctimas y atender retiros; el siguiente despliegue los elimina del índice.

## Desarrollo local

```bash
pip install -r requirements.txt
python build/clonar_fuentes.py
python build/construir_indice.py --fuentes-dir fuentes --salida site/data
python build/compilar_personas.py --salida site/data
cp -r app/. site/ && cd site && python -m http.server 8000
# Pruebas (datos sintéticos): ver .github/workflows/pruebas.yml
```

## Limitaciones

- El OCR comete errores (nombres deformados, páginas ilegibles). Verifica siempre contra el original.
- Los documentos contienen denuncias **no verificadas**. Las menciones automáticas no están clasificadas ni revisadas.
- Que una persona no aparezca no prueba que no aparezca en los documentos.
- Proyecto sin asesoría legal incluida: consulta a un abogado antes de publicarlo.

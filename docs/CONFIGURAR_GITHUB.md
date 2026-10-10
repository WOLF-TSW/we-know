# Configuración recomendada del repositorio

1. **Settings → Branches → Add rule** para `main`:
   - Require a pull request before merging
   - Require approvals: **2**
   - Require review from Code Owners
   - Require status checks: `Validar entradas / validar`
   - Dismiss stale approvals when new commits are pushed
   - Do not allow bypassing the above settings
2. **Teams:** crea `revisores` (aprueban entradas) y `mantenedores` (política y scripts). Actualiza `.github/CODEOWNERS`.
3. **Labels:** `en-disputa`, `correccion`, `prioridad`, `homonimo`.
4. **Verificación contra el índice (opcional pero recomendada):** monta tu índice de texto OCR
   en el runner (o expónlo por API) y define `INDICE_TEXTO`. Formato esperado:
   `INDICE_TEXTO/<id_documento>.txt`, con las páginas separadas por salto de página (`\f`).
   Ejecuta: `python scripts/validar_entradas.py personas --indice $INDICE_TEXTO`
5. **Términos de uso y aviso legal:** publícalos y revísalos con un abogado antes del lanzamiento.

## GitHub Pages y APK

1. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
2. Ejecuta el workflow **Publicar app e índice** manualmente la primera vez.
3. Si el repo es privado, Pages requiere plan que lo permita; el APK usa la URL pública de Pages.
4. Para publicar el APK en una release: `git tag v1.0.0 && git push --tags`.
5. Para Google Play, añade tu keystore como *secret* y cambia `assembleDebug` por `bundleRelease` firmado.

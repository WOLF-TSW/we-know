#!/usr/bin/env python3
"""Valida las entradas de personas de la wiki.

Uso:
  python scripts/validar_entradas.py personas
  python scripts/validar_entradas.py personas --indice /ruta/indice_texto
  python scripts/validar_entradas.py ejemplos --permitir-ejemplo

Comprueba: estructura, fuentes oficiales, lenguaje neutral, longitud de citas,
atribucion, ausencia de datos de victimas y (opcional) que la cita exista en el indice.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import yaml

try:
    from rapidfuzz import fuzz
except ImportError:  # verificacion tolerante opcional
    fuzz = None

DOMINIOS_OFICIALES = {
    "justice.gov", "oversight.house.gov", "democrats-oversight.house.gov",
    "vault.fbi.gov", "courtlistener.com", "uscourts.gov", "govinfo.gov",
}
FUENTES = {"DOJ", "COMITE_CAMARA", "FBI_VAULT", "TRIBUNAL"}
CATEGORIAS = {
    "registro_de_vuelos", "correspondencia", "testimonio", "agenda_de_contactos",
    "mencion_pasajera", "documento_financiero", "denuncia_no_verificada", "otro",
}
VERIFICACIONES = {"documentada", "denuncia_no_verificada", "ilegible_ocr"}
ESTADOS = {"vivo", "fallecido", "desconocido"}
MAX_PALABRAS_CITA = 40
MAX_CONTEXTO = 500

# Terminos que insinuan culpabilidad/inocencia o vinculos. Se buscan en `contexto`.
PROHIBIDAS = [
    "culpable", "inocente", "pedofil", "pederast", "violador", "abusador",
    "criminal", "delincuente", "complice", "traficante", "depredador",
    "implicad", "involucrad", "vinculad", "salpicad", "sin duda", "obviamente",
    "claramente", "evidentemente", "demuestra que", "prueba que", "confirma que",
    "guilty", "innocent", "pedophile", "predator", "accomplice",
]


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def slug(nombre: str) -> str:
    base = normalizar(nombre)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def dominio_oficial(url: str) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(
        host == d or host.endswith("." + d) for d in DOMINIOS_OFICIALES
    )


def verificar_cita(indice: Path, id_doc: str, pagina: int, cita: str):
    """Devuelve (ok, mensaje). Formato: indice/<id_documento>.txt, paginas separadas por \\f."""
    archivo = indice / f"{id_doc}.txt"
    if not archivo.exists():
        return None, f"documento {id_doc} no esta en el indice (no se pudo verificar)"
    paginas = archivo.read_text(encoding="utf-8", errors="ignore").split("\f")
    if not (1 <= pagina <= len(paginas)):
        return False, f"pagina {pagina} fuera de rango (el documento tiene {len(paginas)})"
    texto, c = normalizar(paginas[pagina - 1]), normalizar(cita)
    if c in texto:
        return True, ""
    if fuzz is not None and fuzz.partial_ratio(c, texto) >= 90:
        return True, ""
    return False, "la cita no aparece en esa pagina del documento"


def validar_archivo(ruta: Path, permitir_ejemplo: bool, indice):
    errores, avisos = [], []
    try:
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"YAML invalido: {e}"], avisos
    if not isinstance(datos, dict):
        return ["el archivo debe ser un mapa YAML"], avisos

    nombre = datos.get("nombre")
    if not isinstance(nombre, str) or len(nombre.strip()) < 3:
        errores.append("falta 'nombre'")
    elif not permitir_ejemplo and ruta.stem != slug(nombre):
        errores.append(f"el archivo debe llamarse '{slug(nombre)}.yml'")
    if datos.get("estado") not in ESTADOS:
        errores.append(f"'estado' debe ser uno de {sorted(ESTADOS)}")
    if not isinstance(datos.get("alias", []), list):
        errores.append("'alias' debe ser una lista")

    menciones = datos.get("menciones")
    if not isinstance(menciones, list) or not menciones:
        errores.append("debe haber al menos una mencion")
        return errores, avisos

    ids = set()
    for i, m in enumerate(menciones, 1):
        p = f"mencion #{i}"
        if not isinstance(m, dict):
            errores.append(f"{p}: formato invalido")
            continue
        mid = m.get("id")
        if not mid or mid in ids:
            errores.append(f"{p}: 'id' ausente o repetido")
        ids.add(mid)
        p = f"mencion {mid or i}"

        doc = m.get("documento") or {}
        if doc.get("fuente") not in FUENTES:
            errores.append(f"{p}: 'documento.fuente' debe ser uno de {sorted(FUENTES)}")
        if not doc.get("id_documento"):
            errores.append(f"{p}: falta 'documento.id_documento'")
        pagina = doc.get("pagina")
        if not isinstance(pagina, int) or isinstance(pagina, bool) or pagina < 1:
            errores.append(f"{p}: 'documento.pagina' debe ser un entero >= 1")
        if not dominio_oficial(str(doc.get("url", ""))):
            errores.append(f"{p}: la URL debe ser https y de una fuente oficial {sorted(DOMINIOS_OFICIALES)}")

        cita = m.get("cita")
        if not isinstance(cita, str) or not cita.strip():
            errores.append(f"{p}: falta 'cita'")
        elif len(cita.split()) > MAX_PALABRAS_CITA:
            errores.append(f"{p}: la cita supera {MAX_PALABRAS_CITA} palabras")

        if m.get("categoria") not in CATEGORIAS:
            errores.append(f"{p}: 'categoria' invalida")
        if m.get("verificacion") not in VERIFICACIONES:
            errores.append(f"{p}: 'verificacion' invalida")
        atrib = m.get("atribucion")
        if not isinstance(atrib, str) or len(atrib.strip()) < 5:
            errores.append(f"{p}: falta 'atribucion' (quien lo afirma)")
        if not isinstance(m.get("posible_homonimo"), bool):
            errores.append(f"{p}: 'posible_homonimo' debe ser true/false")
        if m.get("contiene_datos_de_victimas") is not False:
            errores.append(f"{p}: 'contiene_datos_de_victimas' debe ser false (no se aceptan datos de victimas)")

        # Coherencia denuncia / verificacion
        if m.get("categoria") == "denuncia_no_verificada" and m.get("verificacion") != "denuncia_no_verificada":
            errores.append(f"{p}: una denuncia no verificada debe llevar verificacion: denuncia_no_verificada")

        ctx = m.get("contexto")
        if not isinstance(ctx, str) or not ctx.strip():
            errores.append(f"{p}: falta 'contexto'")
        else:
            if len(ctx) > MAX_CONTEXTO:
                errores.append(f"{p}: 'contexto' supera {MAX_CONTEXTO} caracteres")
            n = normalizar(ctx)
            for palabra in PROHIBIDAS:
                if palabra in n:
                    errores.append(f"{p}: lenguaje no neutral en 'contexto' ('{palabra}'). Describe el documento, no concluyas sobre la persona")

        # Verificacion contra el indice (opcional)
        if indice and isinstance(cita, str) and isinstance(pagina, int) and doc.get("id_documento"):
            ok, msg = verificar_cita(indice, str(doc["id_documento"]), pagina, cita)
            if ok is False:
                errores.append(f"{p}: {msg}")
            elif ok is None:
                avisos.append(f"{p}: {msg}")
    return errores, avisos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", help="carpeta con archivos .yml (p. ej. personas)")
    ap.add_argument("--indice", help="carpeta con el indice de texto para verificar citas")
    ap.add_argument("--permitir-ejemplo", action="store_true", help="no exige que el nombre del archivo coincida con la persona")
    args = ap.parse_args()

    carpeta = Path(args.carpeta)
    indice = Path(args.indice) if args.indice else None
    archivos = sorted(p for p in carpeta.glob("*.yml") if not p.name.startswith("_"))
    if not archivos:
        print(f"No hay entradas en {carpeta} (nada que validar).")
        return 0

    total_err = 0
    for f in archivos:
        errores, avisos = validar_archivo(f, args.permitir_ejemplo, indice)
        for a in avisos:
            print(f"AVISO  {f}: {a}")
        for e in errores:
            print(f"ERROR  {f}: {e}")
        if not errores:
            print(f"OK     {f}")
        total_err += len(errores)

    print(f"\n{len(archivos)} archivo(s), {total_err} error(es).")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())

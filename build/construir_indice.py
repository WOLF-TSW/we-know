#!/usr/bin/env python3
"""Construye un indice estatico de busqueda (sin servidor) a partir de repos de GitHub con texto OCR.

Salida (carpeta --salida):
  manifest.json        metadatos
  comunes.json         tokens demasiado frecuentes (no se indexan)
  idx/<xx>.json        indice invertido por las 2 primeras letras: {token: [deltas de doc-id]}
  t/<n>.json           paquetes de texto: lista de documentos con sus paginas

Uso:
  python build/construir_indice.py --fuentes-dir fuentes --config build/fuentes.json --salida site/data
"""
import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TAM_PACK = 200
FRACCION_COMUN = 0.4
MIN_DOCS_PARA_COMUNES = 50
MAX_TOKEN = 30
TOKEN = re.compile(r"[a-z0-9]{3,}")
CLAVES_TEXTO = ("full_text", "text", "content", "texto", "ocr_text", "raw_text")
CLAVES_BLOQUES = ("text_blocks", "blocks", "lines", "paragraphs", "segments")
IGNORAR = {"filename", "file", "path", "url", "image", "id", "hash", "sha256", "model"}
PAGINA_RETIRADA = "[pagina retirada]"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def clave_natural(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def extraer_texto(obj, prof=0) -> str:
    """Extrae texto de JSON de OCR con esquema desconocido (heuristica tolerante)."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return "\n".join(t for t in (extraer_texto(x, prof + 1) for x in obj) if t)
    if isinstance(obj, dict):
        for k in CLAVES_TEXTO:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for k in CLAVES_BLOQUES:
            v = obj.get(k)
            if isinstance(v, list):
                t = extraer_texto(v, prof + 1)
                if t.strip():
                    return t
        partes = []
        for k, v in obj.items():
            if k in IGNORAR:
                continue
            if isinstance(v, (dict, list)) and prof < 4:
                partes.append(extraer_texto(v, prof + 1))
            elif isinstance(v, str) and len(v) > 20:
                partes.append(v)
        return "\n".join(p for p in partes if p)
    return ""


def cargar_analisis(raiz: Path) -> dict:
    p = raiz / "analyses.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    items = data.items() if isinstance(data, dict) else enumerate(data if isinstance(data, list) else [])
    salida = {}
    for k, v in items:
        if not isinstance(v, dict):
            continue
        clave = next((v[c] for c in ("filename", "file", "image", "path", "document", "id") if isinstance(v.get(c), str)), None)
        if clave is None and isinstance(k, str):
            clave = k
        if not clave:
            continue
        an = v.get("analysis") if isinstance(v.get("analysis"), dict) else v
        resumen = next((an[c] for c in ("summary", "resumen") if isinstance(an.get(c), str)), "")
        tipo = next((an[c] for c in ("document_type", "type", "tipo") if isinstance(an.get(c), str)), "")
        salida[Path(clave).stem.lower()] = (resumen[:400], tipo[:80])
    return salida


def cargar_retiros(ruta: Path):
    docs, frases = set(), []
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith("doc:"):
                docs.add(linea[4:].strip())
            elif linea.startswith("texto:"):
                f = norm(linea[6:].strip())
                if f:
                    frases.append(f)
    return docs, frases


def leer_documentos(fuente: dict, base: Path):
    """Agrupa archivos por carpeta: cada carpeta = documento, cada archivo = pagina."""
    raiz = base / fuente["nombre"]
    ruta = raiz / fuente.get("ruta", "")
    if not ruta.exists():
        print(f"AVISO: no existe {ruta}; fuente omitida", file=sys.stderr)
        return
    analisis = cargar_analisis(raiz)
    grupos = defaultdict(list)
    for p in ruta.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".json", ".txt", ".md") and p.name != "analyses.json":
            rel = p.parent.relative_to(ruta)
            grupos[str(rel) if str(rel) != "." else p.stem].append(p)
    repo, rama = fuente["repo"], fuente.get("rama", "main")
    for doc_id in sorted(grupos):
        paginas, etiquetas = [], []
        for f in sorted(grupos[doc_id], key=clave_natural):
            try:
                if f.suffix.lower() == ".json":
                    texto = extraer_texto(json.loads(f.read_text(encoding="utf-8", errors="ignore")))
                else:
                    texto = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            texto = re.sub(r"[ \t]+", " ", texto).strip()
            if texto:
                paginas.append(texto)
                etiquetas.append(f.stem)
        if not paginas:
            continue
        stems = [Path(doc_id).name.lower()] + [e.lower() for e in etiquetas]
        resumen, tipo = next((analisis[s] for s in stems if s in analisis), ("", ""))
        sub = f"{fuente.get('ruta','')}/{doc_id}".strip("/")
        yield {
            "id": f"{fuente['nombre']}/{doc_id}",
            "titulo": Path(doc_id).name,
            "paginas": paginas,
            "etiquetas": etiquetas,
            "resumen": resumen,
            "tipo": tipo,
            "url": f"https://github.com/{repo}/tree/{rama}/{sub}",
        }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fuentes-dir", default="fuentes")
    ap.add_argument("--config", default="build/fuentes.json")
    ap.add_argument("--retirados", default="build/retirados.txt")
    ap.add_argument("--salida", default="site/data")
    args = ap.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    ret_docs, ret_frases = cargar_retiros(Path(args.retirados))
    salida = Path(args.salida)
    (salida / "idx").mkdir(parents=True, exist_ok=True)
    (salida / "t").mkdir(parents=True, exist_ok=True)

    docs = []
    for fuente in config:
        for d in leer_documentos(fuente, Path(args.fuentes_dir)):
            if d["id"] in ret_docs or d["id"].split("/", 1)[-1] in ret_docs:
                continue
            for i, pg in enumerate(d["paginas"]):
                if any(f in norm(pg) for f in ret_frases):
                    d["paginas"][i] = PAGINA_RETIRADA
            docs.append(d)

    n_docs = len(docs)
    postings = defaultdict(set)
    n_paginas = 0
    for i, d in enumerate(docs):
        n_paginas += len(d["paginas"])
        texto = norm(" ".join(p for p in d["paginas"] if p != PAGINA_RETIRADA))
        for tk in set(TOKEN.findall(texto)):
            if len(tk) <= MAX_TOKEN:
                postings[tk].add(i)

    comunes = set()
    if n_docs >= MIN_DOCS_PARA_COMUNES:
        limite = FRACCION_COMUN * n_docs
        comunes = {t for t, s in postings.items() if len(s) > limite}
    shards = defaultdict(dict)
    for tk, s in postings.items():
        if tk in comunes:
            continue
        prev, deltas = 0, []
        for v in sorted(s):
            deltas.append(v - prev)
            prev = v
        shards[tk[:2]][tk] = deltas
    for k, mapa in shards.items():
        (salida / "idx" / f"{k}.json").write_text(json.dumps(mapa, separators=(",", ":")), encoding="utf-8")

    for n in range((n_docs + TAM_PACK - 1) // TAM_PACK):
        paquete = []
        for i in range(n * TAM_PACK, min(n_docs, (n + 1) * TAM_PACK)):
            d = docs[i]
            paquete.append({"i": i, "t": d["titulo"], "p": d["paginas"], "l": d["etiquetas"],
                            "s": d["resumen"], "y": d["tipo"], "u": d["url"]})
        (salida / "t" / f"{n}.json").write_text(json.dumps(paquete, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    (salida / "comunes.json").write_text(json.dumps(sorted(comunes)), encoding="utf-8")
    (salida / "manifest.json").write_text(json.dumps({
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "documentos": n_docs, "paginas": n_paginas, "tam_pack": TAM_PACK,
        "fuentes": [{"nombre": f["nombre"], "repo": f["repo"]} for f in config],
    }, indent=2), encoding="utf-8")
    print(f"Indice listo: {n_docs} documentos, {n_paginas} paginas, {len(postings)} terminos ({len(comunes)} comunes omitidos).")
    if n_docs == 0:
        print("ERROR: no se indexo ningun documento. Revisa 'ruta' en build/fuentes.json.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

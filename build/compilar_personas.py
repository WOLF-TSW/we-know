#!/usr/bin/env python3
"""Valida y compila personas/*.yml a JSON para la app. Uso: python build/compilar_personas.py --salida site/data"""
import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validar_entradas import normalizar, slug, validar_archivo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--personas", default="personas")
    ap.add_argument("--salida", default="site/data")
    args = ap.parse_args()

    destino = Path(args.salida) / "personas"
    destino.mkdir(parents=True, exist_ok=True)
    indice, fallos = [], 0
    for f in sorted(Path(args.personas).glob("*.yml")):
        if f.name.startswith("_"):
            continue
        errores, _ = validar_archivo(f, False, None)
        if errores:
            fallos += 1
            for e in errores:
                print(f"ERROR {f}: {e}", file=sys.stderr)
            continue
        datos = yaml.safe_load(f.read_text(encoding="utf-8"))
        s = slug(datos["nombre"])
        (destino / f"{s}.json").write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        indice.append({"slug": s, "nombre": datos["nombre"], "alias": datos.get("alias", []),
                       "claves": sorted({normalizar(datos["nombre"]), *[normalizar(a) for a in datos.get("alias", [])]})})
    (destino / "index.json").write_text(json.dumps(indice, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(indice)} persona(s) compilada(s), {fallos} con errores.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())

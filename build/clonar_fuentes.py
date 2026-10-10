#!/usr/bin/env python3
"""Clona (superficialmente) los repos de GitHub listados en build/fuentes.json dentro de ./fuentes/."""
import json
import subprocess
import sys
from pathlib import Path

for f in json.loads(Path("build/fuentes.json").read_text(encoding="utf-8")):
    destino = Path("fuentes") / f["nombre"]
    if destino.exists():
        continue
    r = subprocess.run(["git", "clone", "--depth", "1", "--branch", f.get("rama", "main"),
                        f"https://github.com/{f['repo']}.git", str(destino)])
    if r.returncode != 0:
        print(f"ERROR: no se pudo clonar {f['repo']}", file=sys.stderr)
        sys.exit(1)

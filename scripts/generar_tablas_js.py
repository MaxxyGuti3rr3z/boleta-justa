#!/usr/bin/env python3
"""Genera cliente/tablas.js desde datos/tarifas/*.json (fuente de verdad)."""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "datos" / "tarifas"
SALIDA = RAIZ / "cliente" / "tablas.js"

datos = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(TABLAS.glob("*.json"))]
SALIDA.parent.mkdir(exist_ok=True)
contenido = ("// Generado por scripts/generar_tablas_js.py — no editar a mano.\n"
             "// Fuente: datos/tarifas/*.json (Boletines Oficiales de Jujuy).\n"
             "export const TABLAS = " +
             json.dumps(datos, ensure_ascii=False, indent=1) + ";\n")
SALIDA.write_text(contenido, encoding="utf-8")
print(f"OK: {len(datos)} cuadros → {SALIDA.relative_to(RAIZ).as_posix()}")

#!/usr/bin/env python3
"""Valida el esquema de los cuadros tarifarios de datos/tarifas/.

Uso:
    python scripts/validar_cuadro.py                       # todos
    python scripts/validar_cuadro.py datos/tarifas/resNNN_YYYY-MM.json

Los archivos que empiezan con "_" (plantillas) se ignoran en la validación
global. No modifica ningún archivo.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TABLAS_DIR = RAIZ / "datos" / "tarifas"
NUMEROS = (int, float)


def _numero(v) -> bool:
    return isinstance(v, NUMEROS) and not isinstance(v, bool)


def validar_archivo(ruta: Path) -> list[str]:
    """Devuelve una lista de errores; vacía si el cuadro es válido."""
    errores: list[str] = []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"no se pudo leer: {e}"]
    if not isinstance(datos, dict):
        return ["la raíz debe ser un objeto JSON"]

    for clave in ("resolucion", "publicacion", "fuente"):
        valor = datos.get(clave)
        if not isinstance(valor, str) or not valor.strip():
            errores.append(f"falta o es inválido: {clave}")
    # La nota puede estar vacía si el trimestre no tuvo pass through.
    if not isinstance(datos.get("nota_pass_through"), str):
        errores.append("falta o es inválido: nota_pass_through")

    fuente = datos.get("fuente")
    if isinstance(fuente, str) and fuente.strip() and not fuente.startswith("https://"):
        errores.append("fuente debe ser una URL https://")

    vigencia = datos.get("vigencia")
    if not isinstance(vigencia, dict):
        errores.append("falta vigencia {desde, hasta}")
    else:
        fechas = {}
        for clave in ("desde", "hasta"):
            valor = vigencia.get(clave)
            try:
                fechas[clave] = date.fromisoformat(str(valor))
            except (TypeError, ValueError):
                errores.append(f"vigencia.{clave} debe ser YYYY-MM-DD")
        if len(fechas) == 2 and fechas["desde"] > fechas["hasta"]:
            errores.append("vigencia.desde es posterior a vigencia.hasta")

    t1 = datos.get("t1_residencial")
    if not isinstance(t1, dict):
        errores.append("falta t1_residencial")
        return errores
    cats = t1.get("categorias")
    if not isinstance(cats, list) or not cats:
        errores.append("t1_residencial.categorias debe ser una lista no vacía")
        return errores

    ids: set[str] = set()
    topes: list[float] = []
    for i, cat in enumerate(cats):
        if not isinstance(cat, dict):
            errores.append(f"categoría {i} no es un objeto")
            continue
        cid = cat.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errores.append(f"categoría {i}: falta id")
        elif cid in ids:
            errores.append(f"categoría {i}: id duplicado ({cid})")
        else:
            ids.add(cid)
        for clave in ("cargo_fijo", "uso_red_kwh", "energia_plena_kwh"):
            valor = cat.get(clave)
            if not _numero(valor) or valor <= 0:
                errores.append(f"categoría {i} ({cid}): {clave} debe ser > 0")
        tope = cat.get("hasta_kwh", "FALTA")
        if tope == "FALTA":
            errores.append(f"categoría {i} ({cid}): falta hasta_kwh")
        elif tope is None:
            if i != len(cats) - 1:
                errores.append(f"categoría {i} ({cid}): hasta_kwh null solo en la última")
        elif not _numero(tope):
            errores.append(f"categoría {i} ({cid}): hasta_kwh debe ser > 0 o null")
        elif tope <= 0:
            errores.append(f"categoría {i} ({cid}): hasta_kwh debe ser > 0 o null")
        else:
            topes.append(tope)

    if topes != sorted(topes):
        errores.append("los bloques (hasta_kwh) no están ordenados")
    if len(set(topes)) != len(topes):
        errores.append("hay topes de bloque repetidos")
    return errores


def validar_todos(carpeta: Path = TABLAS_DIR) -> list[str]:
    """Valida todos los cuadros y chequea que no se solapen las vigencias."""
    archivos = sorted(p for p in carpeta.glob("*.json") if not p.name.startswith("_"))
    errores: list[str] = []
    rangos: list[tuple[str, date, date]] = []
    for archivo in archivos:
        errores += [f"{archivo.name}: {e}" for e in validar_archivo(archivo)]
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        vig = datos.get("vigencia") if isinstance(datos, dict) else None
        if isinstance(vig, dict):
            try:
                rangos.append((archivo.name, date.fromisoformat(vig["desde"]),
                               date.fromisoformat(vig["hasta"])))
            except (KeyError, TypeError, ValueError):
                pass
    for (nombre_a, desde_a, hasta_a), (nombre_b, desde_b, hasta_b) in combinations(rangos, 2):
        if desde_a <= hasta_b and desde_b <= hasta_a:
            errores.append(f"vigencias solapadas: {nombre_a} y {nombre_b}")
    return errores


def main() -> int:
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1])
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        errores = validar_archivo(ruta)
        objetivo = ruta.name
    else:
        errores = validar_todos()
        cantidad = len([p for p in TABLAS_DIR.glob("*.json") if not p.name.startswith("_")])
        objetivo = f"{cantidad} cuadros en datos/tarifas/"
    if errores:
        print("ERRORES:")
        for error in errores:
            print(" -", error)
        return 1
    print(f"OK: esquema válido ({objetivo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

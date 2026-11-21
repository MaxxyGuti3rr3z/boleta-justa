#!/usr/bin/env python3
r"""Limpieza de datos sensibles de Boleta Justa.

Por defecto solo MUESTRA qué se borraría (dry-run). Nunca toca los PDF
originales salvo que se pase --include-originals explícitamente.

Uso:
    python scripts/limpiar_sensibles.py                    # ver qué se borraría
    python scripts/limpiar_sensibles.py --apply            # borrar derivados
    python scripts/limpiar_sensibles.py --apply --include-originals
    python scripts/limpiar_sensibles.py --root /tmp/fixture --apply  # tests

Los derivados (_texto/, _parseado/) se pueden regenerar con
`python src/parser_boletas.py` y `python src/auditoria.py`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BOLETAS = "boletas_reales"
DERIVADOS = ("_texto", "_parseado")


def _tam(paths: list[Path]) -> int:
    return sum(p.stat().st_size for p in paths if p.exists())


def _kb(n: int) -> str:
    return f"{n / 1024:.1f} KB"


def recolectar(raiz: Path) -> dict[str, list[Path]]:
    car = raiz / BOLETAS
    grupos: dict[str, list[Path]] = {"derivados": [], "originales": [], "sueltos": []}
    for sub in DERIVADOS:
        d = car / sub
        if d.exists():
            grupos["derivados"].extend(sorted(p for p in d.rglob("*") if p.is_file()))
    if car.exists():
        grupos["originales"].extend(
            sorted(p for p in car.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"))
    # PDFs/imágenes sueltos en la raíz del repo (red de seguridad)
    for p in raiz.iterdir():
        if p.is_file() and p.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg", ".heic", ".webp"):
            grupos["sueltos"].append(p)
    return grupos


def check_git(raiz: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(raiz), "ls-files"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "no se pudo consultar git"
    sensibles = []
    for linea in out.splitlines():
        baja = linea.lower()
        # las capturas de docs/ son de la UI, no datos personales
        if BOLETAS in baja or (baja.endswith((".pdf", ".png", ".jpg", ".jpeg", ".heic", ".webp"))
                               and not baja.startswith("docs/")):
            sensibles.append(linea)
    return ("OK: nada sensible trackeado por git" if not sensibles
            else "ALERTA: archivos sensibles en git: " + ", ".join(sensibles))


def borrar(paths: list[Path]) -> int:
    n = 0
    for p in paths:
        try:
            p.unlink()
            n += 1
        except OSError as e:
            print(f"  no se pudo borrar {p.name}: {e}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="borrar derivationes (por defecto solo mostrar)")
    ap.add_argument("--include-originals", action="store_true",
                    help="incluir los PDF originales (¡irreversible sin backup!)")
    ap.add_argument("--root", type=Path, default=RAIZ, help="raíz del proyecto (para tests)")
    args = ap.parse_args()

    raiz = args.root.resolve()
    grupos = recolectar(raiz)
    derivados = grupos["derivados"]
    originales = grupos["originales"] if args.include_originals else []
    sueltos = grupos["sueltos"]

    print(f"Raíz: {raiz}")
    print("\nDERIVADOS (se pueden regenerar):")
    for p in derivados:
        print(f"  {p.relative_to(raiz)}  {_tam([p]) / 1024:.1f} KB")
    if not derivados:
        print("  (ninguno)")
    print(f"  total: {len(derivados)} archivos, {_kb(_tam(derivados))}")

    print("\nPDFs ORIGINALES:")
    for p in grupos["originales"]:
        marca = "→ SE BORRARÁN" if args.include_originals else "→ se conservan (usa --include-originals)"
        print(f"  {p.name}  {_tam([p]) / 1024:.1f} KB  {marca}")
    if not grupos["originales"]:
        print("  (ninguno)")

    if sueltos:
        print("\nSUELTOS FUERA DE boletas_reales/:")
        for p in sueltos:
            print(f"  {p.name}")

    borrar_todos = derivados + originales + sueltos
    print(f"\n{check_git(raiz)}")
    if not args.apply:
        print(f"\nMODO DRY-RUN: no se borró nada. {len(borrar_todos)} archivos marcados.")
        print("Pasá --apply para borrar los derivados; agregá --include-originals para los PDF.")
        return 0

    print("\nBORRANDO…")
    n = borrar(borrar_todos)
    # limpiar directorios derivados vacíos
    for sub in DERIVADOS:
        d = raiz / BOLETAS / sub
        if d.exists() and not any(d.iterdir()):
            try:
                d.rmdir()
                print(f"  directorio vacío eliminado: {d.relative_to(raiz)}")
            except OSError:
                pass
    print(f"Borrados {n} de {len(borrar_todos)} archivos marcados.")
    if originales:
        print("ATENCIÓN: se borraron PDFs originales. No se pueden recuperar sin backup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

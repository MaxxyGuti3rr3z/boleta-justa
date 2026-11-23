"""Paridad: los MISMOS casos sintéticos se ejecutan en Python y en JS."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
import tarifas
import auditoria

CASOS = RAIZ / "pruebas" / "casos_paridad"
TABLAS = auditoria.cargar_tablas()
RES297 = next(t for t in TABLAS if t["resolucion"].startswith("297"))
FALLOS = []


def comparar(caso, obtenido, esperado):
    if obtenido != esperado:
        claves = sorted(set(esperado) | set(obtenido))
        diffs = [f"{k}: Python={esperado.get(k)!r} JS/actual={obtenido.get(k)!r}"
                 for k in claves if esperado.get(k) != obtenido.get(k)]
        FALLOS.append(f"{caso['id']}: " + " | ".join(diffs))


def main():
    archivos = sorted(CASOS.glob("*.json"))
    if not archivos:
        FALLOS.append("no hay casos en pruebas/casos_paridad/")
    for archivo in archivos:
        caso = json.loads(archivo.read_text(encoding="utf-8"))
        e = caso["entrada"]
        if caso["tipo"] == "calcular":
            opciones = {k: v for k, v in e.items() if k not in ("kwh", "mes")}
            obtenido = tarifas.calcular(e["kwh"], e.get("mes", "2026-08"),
                                        tarifas=RES297, **opciones)
        elif caso["tipo"] == "auditar":
            obtenido = auditoria.auditar(e, TABLAS)
        else:
            FALLOS.append(f"{caso['id']}: tipo desconocido {caso['tipo']}")
            continue
        comparar(caso, obtenido, caso["esperado"])

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print(f"OK: {len(archivos)} casos de paridad (esperados generados desde src/)")


if __name__ == "__main__":
    main()

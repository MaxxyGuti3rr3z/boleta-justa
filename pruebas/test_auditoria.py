"""Tests de auditoría con boletas SINTÉTICAS (nunca datos reales).
Uso: py -3.13 pruebas/test_auditoria.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import auditoria as au  # noqa: E402


def main():
    fallos = []

    def check(cond, msg):
        if not cond:
            fallos.append(msg)

    tablas = au.cargar_tablas()
    check(len(tablas) >= 4, f"esperaba >=4 cuadros, hay {len(tablas)}")
    check(au.mes_de("13/02/2026") == "2026-02", "mes_de")
    check(au.mes_de(None) is None, "mes_de None")

    # boleta sintética mayo/jun-2026: todo coincide con Res 227
    b = {"fecha_emision": "10/06/2026", "categoria": "T1TS",
         "energia": {"cargo_fijo": 4772.0, "precio_red": 88.8382,
                     "precio_consumo": 149.9075}, "punitorios_detectados": False}
    r = au.auditar(b, tablas)
    check(r["resolucion"] == "227-SUSEPU/2026", f"res: {r['resolucion']}")
    check(r["cargo_fijo_ok"] and r["uso_red_ok"] and r["energia_ok"], f"coincidencias: {r}")
    check(r["categoria_tabla"] == "R1", f"cat: {r['categoria_tabla']}")

    # jul-2026: energía con pass through distinto → DIFIERE con porcentaje
    b2 = {**b, "fecha_emision": "10/07/2026",
          "energia": {**b["energia"], "precio_consumo": 158.2890}}
    r2 = au.auditar(b2, tablas)
    check(not r2["energia_ok"], "energía julio debía diferir del valor may-jun")
    check(r2["energia_diff_pct"] and r2["energia_diff_pct"] > 5,
          f"diff: {r2['energia_diff_pct']}")
    check(r2["cargo_fijo_ok"] and r2["uso_red_ok"], "VAD no cambia en el trimestre")

    # feb-2026 → Res 81; nov-2025 → Res 420
    b3 = {**b, "fecha_emision": "13/02/2026",
          "energia": {"cargo_fijo": 4512.0, "precio_red": 84.0110,
                      "precio_consumo": 141.7247}}
    check(au.auditar(b3, tablas)["resolucion"] == "81-SUSEPU/2026", "res feb")
    b4 = {**b, "fecha_emision": "20/11/2025",
          "energia": {"cargo_fijo": 4218.0, "precio_red": 78.5342,
                      "precio_consumo": 120.9237}}
    r4 = au.auditar(b4, tablas)
    check(r4["resolucion"] == "420-SUSEPU/2025", "res nov")
    check(r4["cargo_fijo_ok"] and r4["uso_red_ok"] and r4["energia_ok"], "nov coincide")

    # mar-2025: no hay cuadro por fecha (pero el VAD igual permite identificar uno)
    b5 = {**b, "fecha_emision": "05/03/2025"}
    r5 = au.auditar(b5, tablas)
    check(r5["resolucion_por_fecha"] is None, "mes sin cuadro por fecha")
    check(r5["estado"] == "auditada", "selección por VAD funciona sin fecha")
    b6 = {**b, "energia": {}}
    check(au.auditar(b6, tablas)["estado"] == "sin_cuadro_cargado", "sin datos VAD")

    # punitorios: solo señal dentro de la vigencia del Decreto 5658 (desde 20/07/2026)
    b7 = {**b, "fecha_emision": "05/08/2026", "punitorios_detectados": True}
    check(au.auditar(b7, tablas)["punitorios_en_vigencia"], "punitorios dentro de vigencia")
    b8 = {**b, "fecha_emision": "05/02/2026", "punitorios_detectados": True}
    check(not au.auditar(b8, tablas)["punitorios_en_vigencia"], "punitorios fuera de vigencia")

    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print(" -", f)
        sys.exit(1)
    print("OK: 4 cuadros, selección por mes, VAD exacto, pass through julio, mes sin cuadro")


if __name__ == "__main__":
    main()

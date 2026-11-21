"""Tests de la calculadora tarifaria. Uso: python pruebas/test_tarifas.py
Valores esperados calculados a mano desde el Anexo I de la Res. 297-SUSEPU/2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import tarifas  # noqa: E402


def main():
    fallos = []

    def check(cond, msg):
        if not cond:
            fallos.append(msg)

    def cerca(a, b, tol=0.02):
        return abs(a - b) <= tol

    t = tarifas.cargar()

    # límites de categoría (R1 ≤150, R2 ≤300, R3 ≤500, R4 ≤700, R5 ≤1400, R6 ≤4800, R7 >4800)
    for kwh, esperado in [(0, "R1"), (150, "R1"), (151, "R2"), (300, "R2"),
                          (301, "R3"), (500, "R3"), (501, "R4"), (700, "R4"),
                          (701, "R5"), (1400, "R5"), (1401, "R6"), (4800, "R6"),
                          (4801, "R7"), (10000, "R7")]:
        got = tarifas.categoria_por_consumo(kwh, t)["id"]
        check(got == esperado, f"categoría {kwh} kWh: esperaba {esperado}, dio {got}")
    try:
        tarifas.categoria_por_consumo(-5, t)
        fallos.append("consumo negativo debía rechazarse")
    except ValueError:
        pass

    # caso A: 100 kWh pleno (R1): 5116 + 100*95.2480 + 100*159.1174 = 30552.54
    a = tarifas.calcular(100, tarifas=t)
    check(a["categoria"] == "R1", "caso A categoría")
    check(cerca(a["subtotal_tarifario"], 5116 + 9524.80 + 15911.74),
          f"caso A subtotal: {a['subtotal_tarifario']}")

    # caso B: 200 kWh pleno (R2): 6058 + 200*96.8062 + 200*159.1961 = 57258.46
    b = tarifas.calcular(200, tarifas=t)
    check(b["categoria"] == "R2", "caso B categoría")
    check(cerca(b["subtotal_tarifario"], 6058 + 19361.24 + 31839.22),
          f"caso B subtotal: {b['subtotal_tarifario']}")

    # caso C: 200 kWh con Tarifa Social + SEF (ago-2026)
    # fijo: 6058-6058=0 | red: 19361.24-(150*23.8120+50*14.5210)=15063.39
    # energía: 31839.22-(150*93.2206+50*93.2730)=13192.48 | total 28255.87
    c = tarifas.calcular(200, tarifa_social=True, sef=True, tarifas=t)
    check(cerca(c["descuento_tarifa_social_fijo"], 6058), f"C d_ts_fijo: {c['descuento_tarifa_social_fijo']}")
    check(cerca(c["descuento_tarifa_social_red"], 3571.80 + 726.05), f"C d_ts_red: {c['descuento_tarifa_social_red']}")
    check(cerca(c["descuento_sef_energia"], 13983.09 + 4663.65), f"C d_sef: {c['descuento_sef_energia']}")
    check(cerca(c["subtotal_tarifario"], 28255.87), f"C subtotal: {c['subtotal_tarifario']}")

    # caso D: 400 kWh TS+SEF → R3; fijo sin bonificación publicada (>300) con nota;
    # red y energía bonificadas solo hasta 300 kWh (bloque 2 completo: 150 kWh)
    d = tarifas.calcular(400, tarifa_social=True, sef=True, tarifas=t)
    check(d["categoria"] == "R3", "caso D categoría")
    check(cerca(d["cargo_fijo"], 10180), "D fijo pleno")
    check(any(">300" in n for n in d["notas"]), "D nota de verificación >300")
    check(cerca(d["descuento_tarifa_social_red"], 3571.80 + 2178.15), "D red tope 300")
    check(cerca(d["descuento_sef_energia"], 13983.09 + 13990.95), "D SEF tope 300")
    check(any("bloque base" in n for n in d["notas"]), "D nota excedente SEF")

    # caso E: electrodependiente 200 kWh → categoría RE, componentes ~0
    e = tarifas.calcular(200, electrodependiente=True, tarifas=t)
    check(e["categoria"] == "RE", f"E categoría: {e['categoria']}")
    check(cerca(e["subtotal_tarifario"], 0, tol=1.0), f"E subtotal: {e['subtotal_tarifario']}")

    # mes sin bonificaciones cargadas + subsidios → error explícito (no inventar)
    try:
        tarifas.calcular(200, mes="2026-09", tarifa_social=True, tarifas=t)
        fallos.append("septiembre con subsidios debía fallar (sin anexo cargado)")
    except ValueError as ex:
        check("bonificaciones" in str(ex), f"mensaje inesperado: {ex}")
    # septiembre pleno: dentro del trimestre ago-oct (sin nota de vigencia);
    # el pass through nacional puede cambiar precios, pero el cuadro cubre el trimestre
    s = tarifas.calcular(200, mes="2026-09", tarifas=t)
    check(not any("vigencia" in n for n in s["notas"]),
          "septiembre está dentro del trimestre ago-oct, no debía avisar")
    # noviembre (trimestre siguiente) también avisa
    n = tarifas.calcular(200, mes="2026-11", tarifas=t)
    check(any("vigencia" in n for n in n["notas"]), "noviembre debía avisar fuera de vigencia")

    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print(" -", f)
        sys.exit(1)
    print("OK: categorías, plenos, TS+SEF por bloques, topes, electrodependiente, "
          "meses sin cargar (error/nota)")


if __name__ == "__main__":
    main()

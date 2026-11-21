"""Tests del parser con texto SINTÉTICO (nunca datos de boletas reales).
Uso: py -3.13 pruebas/test_parser.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import parser_boletas as pb  # noqa: E402

TEXTO = """
EVOLUCIÓN DEL CONSUMO EN KWH
30 Consumo Diario 1500
30 Días Facturados 30
ENERGÍA ELÉCTRICA
Cargo Fijo 4.772,00
Cargo por Consumo de Energía (156.1556 $/kWh) 19.285,22
Cargo por Uso de Red (88.8382 $/kWh) 10.971,52
Subsidio Estado Nacional – N2 -6.604,57
Bonif. Tarifa Social Provincia -6.250,08
SUBTOTAL ENERGÍA ELÉCTRICA 12.272,81
TASAS E IMPUESTOS
Percep. contrib. única (6%) 736,37
Tasa Fiscalización Susepu 1.5% 402,34
Percep.Alumbrado Publico 3.979,52
IVA Consumidor Final 5.632,79
IVA Intereses % 1.005,94
SUBTOTAL TASAS E IMPUESTOS 11.756,96
OTROS CARGOS
Cargo FOPEJ Res 7-ISPTyV-22 (0,1500 $/kWh) 30,00
Ajuste por Redondeo - Resoluc. N° 48-SUSEPU-25 -12,00
SUBTOTAL OTROS CARGOS 18,00
TOTAL EJESA 24.047,77
EVOLUCIÓN DEL CONSUMO EN M3 SERVICIOS SANITARIOS
Cargo Variable Agua 4,50
Cargo Fijo 3.747,90
TASAS E IMPUESTOS
Iva 21 % 985,54
IVA Interés Punitorio 21% 102,04
SUBTOTAL TASAS E IMPUESTOS 1.245,41
TOTAL 6.630,00
FECHA DE EMISIÓN
13/02/2026
VENCIMIENTO
03/03/2026
TOTAL A PAGAR
30.677,77
"""


def main():
    fallos = []

    def check(cond, msg):
        if not cond:
            fallos.append(msg)

    d = pb.parsear([l.strip() for l in TEXTO.splitlines() if l.strip()])
    e, imp, agua, tot = d["energia"], d["impuestos"], d["agua"], d["totales"]

    check(e.get("cargo_fijo") == 4772.0, f"cargo fijo eléctrico: {e.get('cargo_fijo')}")
    check(e.get("precio_consumo") == 156.1556, f"precio consumo: {e.get('precio_consumo')}")
    check(e.get("cargo_consumo") == 19285.22, f"cargo consumo: {e.get('cargo_consumo')}")
    check(e.get("precio_red") == 88.8382, f"precio red: {e.get('precio_red')}")
    check(e.get("bonif_tarifa_social") == -6250.08, "bonificación TS")
    check(e.get("subtotal") == 12272.81, "subtotal energía")
    check(imp.get("tasa_fiscalizacion") == 402.34, f"tasa fiscalización: {imp.get('tasa_fiscalizacion')}")
    check(imp.get("percepcion_alumbrado") == 3979.52, "percepción alumbrado")
    check(imp.get("subtotal") == 11756.96, "subtotal impuestos")
    check(agua.get("cargo_fijo") == 3747.90, f"cargo fijo agua (no debe pisar el eléctrico): {agua.get('cargo_fijo')}")
    check(e["cargo_fijo"] == 4772.0, "el cargo fijo eléctrico fue sobreescrito por el de agua")
    check(d["punitorios_detectados"] is True, "punitorios detectados")
    check(tot.get("ejesa") == 24047.77, "total EJESA")
    check(tot.get("a_pagar") == 30677.77, f"total a pagar: {tot.get('a_pagar')}")
    check(d.get("fecha_emision") == "13/02/2026", f"fecha emisión: {d.get('fecha_emision')}")
    check(d.get("vencimiento") == "03/03/2026", f"vencimiento: {d.get('vencimiento')}")
    check(d.get("consistencia", {}).get("coincide_a_pagar") is True, "consistencia aritmética")

    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print(" -", f)
        sys.exit(1)
    print("OK: secciones, importes con coma decimal, precios con punto, "
          "tasas, punitorios, total a pagar, fechas, consistencia, sin datos personales")


if __name__ == "__main__":
    main()

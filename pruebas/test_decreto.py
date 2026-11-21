"""Tests del verificador del Decreto 5658-JG/2026. Uso: python pruebas/test_decreto.py"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import decreto  # noqa: E402


def main():
    fallos = []

    def check(cond, msg):
        if not cond:
            fallos.append(msg)

    v = date(2026, 9, 1)  # vencimiento de la segunda factura impaga

    # corte: 19 días → anticipado; 20 → zona gris; 21 → cumplido
    check(decreto.verificar_corte(v, date(2026, 9, 20))["estado"] == "anticipado", "19 días")
    check(decreto.verificar_corte(v, date(2026, 9, 21))["estado"] == "zona_gris", "20 días")
    r = decreto.verificar_corte(v, date(2026, 9, 22))
    check(r["estado"] == "plazo_cumplido" and r["dias_mora_al_corte"] == 21, "21 días")
    check("20" in r["normativa"], "cita del corte")

    # fechas invertidas → error
    try:
        decreto.verificar_corte(date(2026, 9, 22), v)
        fallos.append("corte anterior al vencimiento debía fallar")
    except ValueError:
        pass

    # corte fuera de vigencia (antes del decreto) → nota
    r = decreto.verificar_corte(date(2026, 6, 1), date(2026, 6, 25))
    check(r["estado"] == "plazo_cumplido" and any("vigencia" in n for n in r["notas"]),
          "corte pre-decreto debía avisar")

    # retiro de medidor: 59 días → anticipado; 60 → cumplido
    c = date(2026, 9, 22)
    check(decreto.verificar_retiro_medidor(c, date(2026, 11, 20))["estado"] == "anticipado",
          "retiro 59 días")
    r = decreto.verificar_retiro_medidor(c, date(2026, 11, 21))
    check(r["estado"] == "plazo_cumplido" and r["dias_desde_corte"] == 60, "retiro 60 días")
    try:
        decreto.verificar_retiro_medidor(date(2026, 11, 21), c)
        fallos.append("retiro anterior al corte debía fallar")
    except ValueError:
        pass

    # punitorios: dentro de vigencia con monto → prohibido_cobrado
    r = decreto.verificar_punitorios(1500.0, date(2026, 10, 5))
    check(r["estado"] == "prohibido_cobrado", "punitorios cobrados")
    check(any("1.500,00" in n or "1,500.00" in n for n in r["notas"]), "monto en nota")
    check(decreto.verificar_punitorios(0, date(2026, 10, 5))["estado"] == "sin_punitorios",
          "sin punitorios")
    check(decreto.verificar_punitorios(1500, date(2028, 1, 5))["estado"] == "fuera_de_vigencia",
          "punitorios post-2027")
    try:
        decreto.verificar_punitorios(-1, date(2026, 10, 5))
        fallos.append("monto negativo debía fallar")
    except ValueError:
        pass

    if fallos:
        print(f"FALLOS ({len(fallos)}):")
        for f in fallos:
            print(" -", f)
        sys.exit(1)
    print("OK: plazos de corte (19/20/21), retiro (59/60), punitorios, vigencias, errores")


if __name__ == "__main__":
    main()

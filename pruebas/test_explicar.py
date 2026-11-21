"""Tests de la explicación en lenguaje llano (datos sintéticos, nunca boletas reales)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import explicar

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def base():
    return {"estado": "auditada", "mes": "2026-08", "resolucion": "297-SUSEPU/2026",
            "cargo_fijo_ok": True, "uso_red_ok": True, "bonif_ts_presente": True,
            "energia_ok": True, "energia_diff_pct": 0.0,
            "punitorios_signal": False, "punitorios_en_vigencia": False,
            "categoria_boleta": "T1TS", "uso_red_metodo": "bloques"}


def main():
    a = base()
    r = explicar.explicar(a, {"energia": {}, "consistencia": {"coincide_a_pagar": True}})
    check(r["estado"] == "en_orden", "todo bien → en_orden")
    check("agosto de 2026" in r["titulo"], "mes en lenguaje natural")
    check(not any(i["icono"] == "⚠️" for i in r["items"]), "sin alertas")
    check(len(r["glosario"]) >= 5, "glosario presente")
    check("bonificación" in " ".join(i["texto"] for i in r["items"]), "menciona bonificación TS")

    a2 = {**base(), "energia_ok": False, "energia_diff_pct": 4.2,
          "punitorios_signal": True, "punitorios_en_vigencia": True}
    r2 = explicar.explicar(a2)
    check(r2["estado"] == "a_revisar", "hay alertas → a_revisar")
    textos = " ".join(i["texto"] for i in r2["items"])
    check("4,2%" in textos or "4.2%" in textos, "muestra el porcentaje de energía")
    check("no significa un error" in textos, "pass through no es error")
    check("Decreto 5658" in textos, "cita decreto para punitorios vigentes")

    a3 = {**base(), "punitorios_signal": True, "punitorios_en_vigencia": False}
    r3 = explicar.explicar(a3)
    textos3 = " ".join(i["texto"] for i in r3["items"])
    check("no aplica" in textos3, "punitorios fuera de vigencia no aplica")

    r4 = explicar.explicar({"estado": "sin_cuadro_cargado"}, {})
    check(r4["estado"] == "sin_datos", "sin cuadro → sin_datos")

    r5 = explicar.explicar(base(), {"consistencia": {"coincide_a_pagar": False}})
    check(any("suma no cierra" in i["titulo"] for i in r5["items"]), "suma inconsistente se explica")

    salida = str([r, r2, r3, r4, r5]).lower()
    check(not any(k in salida for k in ("dni", "dirección", "titular", "cuit")),
          "sin datos personales en la explicación")

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: explicación en lenguaje llano, pass through, decreto, consistencia, sin datos personales")


if __name__ == "__main__":
    main()

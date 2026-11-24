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

    sincuadro = explicar.explicar({
        "estado": "cuadro_no_disponible", "mes": "2026-12",
        "mensaje": explicar.MENSAJE_CUADRO_NO_DISPONIBLE})
    check(sincuadro["estado"] == "sin_cuadro", "cuadro no disponible → sin_cuadro")
    check("Todavía no tenemos cargado el cuadro tarifario de este período" in sincuadro["resumen"],
          "aviso en lenguaje llano")
    check("pedirle a EJESA el desglose" in sincuadro["resumen"], "sugiere pedir desglose")
    check(not any(i["icono"] == "⚠️" for i in sincuadro["items"]), "sin veredicto")

    r5 = explicar.explicar(base(), {"consistencia": {"coincide_a_pagar": False}})
    check(any("No pudimos verificar el total" in i["titulo"] for i in r5["items"]),
          "total no verificable se explica")
    check(not any(i["icono"] == "⚠️" and "total" in i["titulo"] for i in r5["items"]),
          "total no verificable no es señal")
    check(r5["estado"] == "en_orden", "total no verificable no cambia el estado")

    r6 = explicar.explicar({**base(), "mes": "2026-03"})
    claves6 = {i.get("clave") for i in r6["items"] if i.get("clave")}
    check(claves6 == {"297"}, "aviso según el cuadro aplicado")
    check(r6["estado"] == "en_orden", "avisos no cambian el estado")
    r7 = explicar.explicar({**base(), "resolucion": "168-SUSEPU/2025"})
    check(not any(i.get("clave") for i in r7["items"]), "sin aviso para cuadros sin nota")
    r8 = explicar.explicar({**base(), "resolucion": "227-SUSEPU/2026", "mes": "2026-08"})
    a227 = next(i for i in r8["items"] if i.get("clave") == "227")
    fuentes227 = " ".join(a227["fuentes"])
    check("227-SUSEPU/2026" in fuentes227, "fuentes del aviso coinciden con el cuadro")
    check(not any(x in fuentes227 for x in ("476-SUSEPU", "105-SUSEPU", "104-SUSEPU")),
          "fuentes ajenas al cuadro no aparecen")

    salida = str([r, r2, r3, r4, r5, r6, r7]).lower()
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

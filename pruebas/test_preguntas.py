"""Tests del payload mínimo para IA y de las preguntas (datos sintéticos)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import payload_ia
import preguntas
import ia_client

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def boleta():
    return {
        "fecha_emision": "20/08/2026", "categoria": "T1TS", "dias_facturados": 31.5,
        "nombre_titular": "NO DEBE SALIR", "direccion": "NO DEBE SALIR",
        "energia": {"cargo_fijo": 4772.0, "cargo_consumo": 26860.0,
                    "precio_consumo": 141.7971, "cargo_red": 16845.0,
                    "precio_red": 88.8382, "bonif_tarifa_social": -7417.13,
                    "subsidio_nacional": -11786.87},
        "impuestos": {"iva_consumidor": 4155.82, "subtotal": 9843.9},
        "agua": {"iva_punitorio": 430.54},
        "totales": {"ejesa": 58500.0, "a_pagar": 58500.0},
    }


def aud():
    return {"estado": "auditada", "resolucion": "297-SUSEPU/2026",
            "categoria_tabla": "R1", "confianza": "alta", "cargo_fijo_ok": True,
            "uso_red_ok": True, "uso_red_metodo": "bloques", "energia_ok": False,
            "energia_diff_pct": 4.2, "bonif_ts_presente": True,
            "punitorios_signal": True, "punitorios_en_vigencia": True}


def main():
    p = payload_ia.construir(boleta(), aud())
    payload_ia.validar(p)
    check(set(p) <= payload_ia.PERMITIDOS, "solo campos permitidos")
    check("nombre_titular" not in str(p) and "direccion" not in str(p), "sin datos personales")
    check(p["consumo_kwh"] == 189.4, "kWh derivado")  # 26860/141.7971 ≈ 189.42 → 189.4
    check(p["mes"] == "2026-08", "mes derivado sin día")

    mal = {**p, "dni": 12345678}
    try:
        payload_ia.validar(mal)
        check(False, "rechaza campo extra")
    except ValueError:
        pass
    try:
        payload_ia.validar({**p, "notas": "Juan Pérez, DNI 12345678"})
        check(False, "rechaza texto personal")
    except ValueError:
        pass

    msgs = payload_ia.mensajes(p, "¿por qué subió?")
    check(len(msgs) == 3, "tres mensajes")
    check("No inventes" in msgs[0]["content"], "prompt prohíbe inventar")
    check("297-SUSEPU/2026" in msgs[1]["content"], "prompt incluye cuadro")
    check("no se envía el PDF" not in msgs[1]["content"], "no menciona PDF")

    a = preguntas.responder("¿por qué me subió la boleta?", p, p["auditoria"])
    check("4.2%" in a["respuesta"] and "pass through" in a["respuesta"], "explica subida")
    check(preguntas.responder("¿qué es el cargo fijo?", p, p["auditoria"])["modo"] == "local",
          "respuesta local")
    check("Decreto 5658" in preguntas.responder("¿hay intereses punitorios?", p, p["auditoria"])["respuesta"],
          "punitorios con decree")
    check(len(preguntas.sugerencias()) >= 4, "sugerencias")

    viejo = dict(os.environ)
    try:
        os.environ.pop("IA_API_URL", None)
        os.environ.pop("IA_API_KEY", None)
        check(not ia_client.configurada(), "IA desactivada por defecto")
        check(ia_client.consultar(msgs) is None, "sin llamada externa")
    finally:
        os.environ.clear()
        os.environ.update(viejo)

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: payload mínimo validado, sin datos personales, preguntas locales, IA opcional")


if __name__ == "__main__":
    main()

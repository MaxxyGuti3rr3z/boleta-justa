"""Respuestas sobre la boleta SIN enviar datos a ningún lado.

Usa el JSON parseado localmente y el resultado de la auditoría. No es un LLM:
cada respuesta sale de los números reales y del cuadro oficial.
"""
from __future__ import annotations


def _pesos(v) -> str:
    if v is None:
        return "no figura en la boleta"
    return "$" + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def responder(pregunta: str, boleta: dict, aud: dict) -> dict:
    p = (pregunta or "").lower()
    e = boleta.get("energia", {})
    imp = boleta.get("impuestos", {})
    agua = boleta.get("agua", {})
    tot = boleta.get("totales", {})
    diff = aud.get("energia_diff_pct") or 0
    res = aud.get("resolucion") or "el cuadro de ese trimestre"

    def r(texto: str, fuente: str = "datos de tu boleta + cuadro oficial") -> dict:
        return {"respuesta": texto, "fuente": fuente, "modo": "local"}

    if any(k in p for k in ("subi", "aument", "más car", "mas car", "caro")):
        partes = []
        if diff > 0:
            partes.append(f"El precio de la luz subió {abs(diff):.1f}% dentro del trimestre. "
                          "Eso lo dispone el gobierno nacional (pass through) y por sí solo "
                          "no es un error de facturación.")
        elif aud.get("energia_ok"):
            partes.append("El precio de la luz coincide con el cuadro oficial de ese trimestre.")
        if imp.get("subtotal"):
            partes.append(f"Los impuestos suman {_pesos(imp.get('subtotal'))} y son una parte "
                          "importante del total (IVA, tasas y alumbrado).")
        if not partes:
            partes.append("No encontré un motivo claro en los datos de la boleta.")
        partes.append("Si querés estar segura/o, pedí el desglose a EJESA y citá la " + res + ".")
        return r(" ".join(partes))

    if "cargo fijo" in p:
        if aud.get("cargo_fijo_ok"):
            return r(f"El cargo fijo es {_pesos(e.get('cargo_fijo'))}: es lo que se paga por "
                     "tener el servicio, aunque gastes poca luz. Coincide con el cuadro " + res + ".")
        return r("El cargo fijo no coincide con el cuadro oficial. Conviene pedir el desglose.")

    if any(k in p for k in ("red", "cable", "poste")):
        return r("El uso de red es lo que se cobra por cables, postes y mantenimiento. "
                 "Se calcula por bloques de consumo (hasta 150 kWh, de 150 a 250, etc.) y "
                 "el precio que figura es un promedio de esos bloques. " +
                 ("En tu boleta coincide con el cuadro oficial." if aud.get("uso_red_ok")
                  else "No pude igualarlo con el cuadro: pedí el desglose."))

    if any(k in p for k in ("interés", "interes", "punitorio", "pago tarde", "atras", "mora")):
        if not aud.get("punitorios_signal"):
            return r("No encontré cargos por pago tardío en esta boleta.")
        if aud.get("punitorios_en_vigencia"):
            return r("La boleta tiene un cargo por pago tardío y su fecha está dentro de la "
                     "vigencia del Decreto 5658, que prohíbe cobrar intereses punitorios "
                     "(Art. 3.C). Es un punto a revisar con EJESA, no un veredicto.")
        return r("Hay un interés por pago tardío, pero la boleta es anterior al Decreto 5658: "
                 "esa prohibición no aplica en este caso.")

    if any(k in p for k in ("tarifa social", "bonific", "descuento", "subsidio")):
        if aud.get("bonif_ts_presente"):
            return r("Tu boleta tiene la bonificación de tarifa social en un renglón propio, "
                     "no descontada del precio de cada kWh. Es un beneficio del Estado para "
                     "hogares que cumplen requisitos.")
        return r("No encontré el renglón de bonificación de tarifa social. Si creés que te "
                 "corresponde, consultalo con EJESA.")

    if any(k in p for k in ("impuesto", "iva", "tasa", "alumbrado")):
        return r(f"Los impuestos y tasas suman {_pesos(imp.get('subtotal'))}. Incluyen IVA "
                 f"({_pesos(imp.get('iva_consumidor'))}), tasa de fiscalización y alumbrado "
                 "público. Son cargos que fija el Estado, no EJESA.")

    if any(k in p for k in ("total", "cuánto", "cuanto", "pagar")):
        return r(f"El total a pagar es {_pesos(tot.get('a_pagar'))}. Incluye luz, impuestos, "
                 "otros cargos y servicios sanitarios. El desglose completo está arriba, "
                 "en la explicación de tu boleta.")

    if any(k in p for k in ("consumo", "kwh", "medidor")):
        return r("El consumo se mide en kWh. Para un hogar, entre 150 y 250 kWh por mes es "
                 "un rango común. Si tu consumo subió, revisá si hubo días extra facturados "
                 "o electrodomésticos nuevos.")

    return r("Puedo responder sobre: por qué subió la boleta, el cargo fijo, el uso de red, "
             "los impuestos, la tarifa social, los intereses por pago tarde y el total. "
             "Probá con alguna de esas palabras.")


def sugerencias() -> list[str]:
    return [
        "¿Por qué me subió la boleta?",
        "¿Qué es el cargo fijo?",
        "¿Qué son los impuestos?",
        "¿Tengo bonificación de tarifa social?",
        "¿Hay intereses por pago tarde?",
    ]

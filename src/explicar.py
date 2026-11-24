"""Explicación en lenguaje llano del resultado de la auditoría.

No incluye importes ni datos personales: convierte los resultados técnicos
en frases que cualquier persona puede entender. Todo el texto que se muestra
en el panel sale de acá.
"""
from __future__ import annotations

try:
    from .auditoria import MENSAJE_CUADRO_NO_DISPONIBLE
except ImportError:  # import directo en tests
    from auditoria import MENSAJE_CUADRO_NO_DISPONIBLE


# Los avisos se eligen por la resolución APLICADA, no por el mes de la boleta:
# así las fuentes mostradas siempre corresponden al cuadro con el que se comparó.
AVISOS = {
    "420": {
        "titulo": "Precios de diciembre y enero: a verificar",
        "texto": "Algunos precios pudieron aplicarse antes del cuadro definitivo. Pedí el desglose por renglón.",
        "detalle": "La Res. 476 aprobó la energía de dic-25/ene-26 y las bonificaciones del Anexo I solo para diciembre de 2025. Sin el desglose no podemos afirmar que el importe sea el final.",
        "fuentes": ["Res. 476-SUSEPU/2025 — Boletín Oficial de Jujuy Nº 149, 29/12/2025"],
    },
    "81": {
        "titulo": "Rectificación publicada después: a verificar",
        "texto": "Después se publicó una rectificación de estos valores. Pedí el desglose para ver cuál se aplicó.",
        "detalle": "La Res. 104 rectificó la Res. 81 para feb-abr/2026 y la Res. 105 documentó bonificaciones adicionales. Lo que comparamos puede no coincidir con lo facturado en su momento.",
        "fuentes": ["Res. 104-SUSEPU/2026 — BO Nº 39, 01/04/2026",
                    "Res. 105-SUSEPU/2026 — BO Nº 39, 01/04/2026"],
    },
    "227": {
        "titulo": "Ajustes durante el trimestre: a verificar",
        "texto": "Los precios pueden ajustarse durante el trimestre. Conviene pedir el desglose.",
        "detalle": "La Res. 227 rige may-jul/2026 y convive con resoluciones nacionales de ajuste. Algunas boletas de ese período se emitieron con valores de la Res. 105 y después se compararon con la 227.",
        "fuentes": ["Res. 227-SUSEPU/2026 — Boletín Oficial de Jujuy",
                    "Res. 297-SUSEPU/2026 (nota sobre boletas de may-jul/2026)"],
    },
    "297": {
        "titulo": "Ajustes durante el trimestre: a verificar",
        "texto": "Los precios pueden ajustarse durante el trimestre. Conviene pedir el desglose.",
        "detalle": "La Res. 297 rige ago-oct/2026 e incorpora variaciones nacionales de precios durante el trimestre; el cargo fijo y el uso de red permanecen fijos.",
        "fuentes": ["Res. 297-SUSEPU/2026 — Boletín Oficial de Jujuy Nº 435659"],
    },
}


def _mes(mes: str | None) -> str:
    nombres = {"01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
               "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
               "09": "septiembre", "10": "octubre", "11": "noviembre",
               "12": "diciembre"}
    if not mes or "-" not in mes:
        return "esa boleta"
    anio, m = mes.split("-")[:2]
    return f"{nombres.get(m, m)} de {anio}"


def explicar(aud: dict, boleta: dict | None = None) -> dict:
    """Devuelve {titulo, estado, periodo, cuadro, resumen, items, acciones, glosario}."""
    boleta = boleta or {}
    items: list[dict] = []
    periodo = _mes(aud.get("mes"))
    cuadro = aud.get("resolucion") or None

    if aud.get("estado") == "cuadro_no_disponible":
        return {
            "titulo": "Todavía no podemos comparar esta boleta",
            "estado": "sin_cuadro", "periodo": periodo, "cuadro": cuadro,
            "resumen": aud.get("mensaje") or MENSAJE_CUADRO_NO_DISPONIBLE,
            "items": [{"icono": "ℹ️", "titulo": "Qué significa",
                       "texto": "Necesitamos el cuadro tarifario oficial de ese trimestre para saber si "
                                "los cargos coinciden. Mientras tanto no podemos afirmar que esté "
                                "bien ni mal."}],
            "acciones": ["Pedile a EJESA el desglose de tu boleta.",
                         "Cuando carguemos el cuadro, vas a poder compararla acá."],
            "glosario": [],
        }

    if aud.get("estado") != "auditada":
        return {
            "titulo": "No pudimos auditar esta boleta",
            "estado": "sin_datos", "periodo": periodo, "cuadro": cuadro,
            "resumen": "No encontramos en el PDF los renglones que necesitamos para comparar. "
                       "Puede ser una boleta de otro formato o de otra empresa.",
            "items": [{"icono": "ℹ️", "titulo": "Qué pasó",
                       "texto": "Probá con una boleta de EJESA de los últimos años."}],
            "acciones": ["Si el PDF está completo y tampoco funciona, contanos para ajustar el lector."],
            "glosario": [],
        }

    # 1. cargo fijo
    if aud.get("cargo_fijo_ok"):
        items.append({"icono": "✅", "titulo": "Cargo fijo: bien",
                      "texto": "Lo que se cobra por tener el servicio coincide con lo que "
                               "estaba aprobado en ese momento."})
    else:
        items.append({"icono": "⚠️", "titulo": "Cargo fijo: a revisar",
                      "texto": "El cargo fijo no coincide con el valor aprobado para ese período."})

    # 2. uso de red
    if aud.get("uso_red_ok"):
        texto = ("Lo que se cobra por usar la red (postes, cables y mantenimiento) "
                 "está bien calculado. Se suma por bloques de consumo, como manda el cuadro.")
        if aud.get("bonif_ts_presente"):
            texto += " Tu boleta también tiene la bonificación de tarifa social en su renglón propio."
        items.append({"icono": "✅", "titulo": "Uso de red: bien", "texto": texto})
    else:
        items.append({"icono": "⚠️", "titulo": "Uso de red: a revisar",
                      "texto": "No pudimos igualar el cargo de red con el cuadro oficial."})

    # 3. energía / pass through
    diff = aud.get("energia_diff_pct") or 0
    if aud.get("energia_ok"):
        items.append({"icono": "✅", "titulo": "Precio de la luz: bien",
                      "texto": "El precio por cada kWh coincide con el cuadro oficial de ese trimestre."})
    elif diff > 0:
        items.append({"icono": "ℹ️", "titulo": "Precio de la luz: cambio durante el trimestre",
                      "texto": f"El precio de la luz en tu boleta es {abs(diff):.1f}% más alto que "
                               "el cuadro base. Eso pasa porque el gobierno actualiza ese precio "
                               "durante el trimestre. Por sí solo no significa un error."})
    else:
        items.append({"icono": "⚠️", "titulo": "Precio de la luz: a revisar",
                      "texto": "El precio por kWh no coincide con el cuadro aprobado."})

    # 4. bonificación social
    if not aud.get("bonif_ts_presente") and aud.get("categoria_boleta", "").startswith("T1T"):
        items.append({"icono": "ℹ️", "titulo": "Tarifa social",
                      "texto": "Tu categoría dice tarifa social, pero no encontramos el renglón "
                               "de la bonificación. Si creés que te corresponde, consultalo con EJESA."})

    # 5. punitorios
    if not aud.get("punitorios_signal"):
        items.append({"icono": "✅", "titulo": "Cargos por pago tarde: ninguno",
                      "texto": "No encontramos intereses por pago tardío en esta boleta."})
    elif aud.get("punitorios_en_vigencia"):
        items.append({"icono": "⚠️", "titulo": "Cargo por pago tarde: a revisar",
                      "texto": "La boleta tiene un cargo de interés por pago tardío. Desde el "
                               "20 de julio de 2026 el Decreto 5658 prohíbe cobrar intereses "
                               "punitorios. Vale la pena pedir el desglose a EJESA."})
    else:
        items.append({"icono": "ℹ️", "titulo": "Cargo por pago tarde",
                      "texto": "Hay un interés por pago tardío, pero la boleta es anterior al "
                               "Decreto 5658: esa prohibición no aplica en este caso."})

    # 6. consistencia aritmética
    consistencia = boleta.get("consistencia", {})
    if consistencia and consistencia.get("coincide_a_pagar") is False:
        items.append({"icono": "ℹ️", "titulo": "No pudimos verificar el total",
                      "texto": "No pudimos comparar la suma de los renglones con el total "
                               "de la boleta. Pedí el desglose para revisarlo."})

    # 7. avisos según la resolución aplicada (no según el mes)
    res_aplicada = str(aud.get("resolucion") or "")
    for clave, aviso in AVISOS.items():
        if res_aplicada.startswith(clave):
            items.append({"icono": "ℹ️", "titulo": aviso["titulo"],
                          "texto": aviso["texto"], "detalle": aviso["detalle"],
                          "fuentes": aviso["fuentes"], "clave": clave})

    revisiones = sum(1 for i in items if i["icono"] == "⚠️")
    if revisiones == 0:
        estado = "en_orden"
        resumen = (f"Comparamos tu boleta de {periodo} con las reglas oficiales "
                   "que correspondían en ese momento. No encontramos nada fuera de lugar.")
    else:
        estado = "a_revisar"
        punto = "punto" if revisiones == 1 else "puntos"
        resumen = (f"Comparamos tu boleta de {periodo} con las reglas oficiales "
                   f"de ese período. Encontramos {revisiones} {punto} que vale la pena revisar.")

    acciones = [
        f"Si querés preguntar por algo, mencioná la resolución {aud.get('resolucion')} "
        "y el mes de la boleta.",
        "Este análisis es una orientación vecinal, no un dictamen legal ni un reclamo automático.",
    ]
    if revisiones:
        acciones.insert(0, "Pedí en EJESA el desglose por renglón antes de pagar o reclamar.")

    glosario = [
        {"termino": "kWh", "significado": "Es la unidad con la que se mide la luz que gastaste. "
                                          "Un ventilador de techo consume poco; un aire acondicionado, mucho."},
        {"termino": "Cargo fijo", "significado": "Un monto que se paga por tener el servicio, "
                                                 "aunque casi no gastes luz."},
        {"termino": "Uso de red", "significado": "El costo de los cables, postes y el mantenimiento "
                                                 "para que la luz llegue a tu casa."},
        {"termino": "Tarifa social", "significado": "Un descuento del Estado para hogares que "
                                                    "cumplen ciertos requisitos. Aparece como un renglón negativo."},
        {"termino": "Pass through", "significado": "Cuando el precio de la luz se actualiza durante "
                                                   "el trimestre por decisión nacional."},
        {"termino": "Interés punitorio", "significado": "Un cargo extra por pagar después de la fecha "
                                                       "de vencimiento."},
    ]
    return {
        "titulo": f"Tu boleta de {periodo}",
        "estado": estado,
        "periodo": periodo,
        "cuadro": cuadro,
        "resumen": resumen,
        "items": items,
        "acciones": acciones,
        "glosario": glosario,
    }

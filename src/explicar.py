"""Explicación en lenguaje llano del resultado de la auditoría.

No incluye importes ni datos personales: convierte los resultados técnicos
en frases que cualquier persona puede entender. Todo el texto que se muestra
en el panel sale de acá.
"""
from __future__ import annotations


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
    """Devuelve {titulo, estado, resumen, items, acciones, glosario}."""
    boleta = boleta or {}
    items: list[dict] = []

    if aud.get("estado") != "auditada":
        return {
            "titulo": "No pudimos auditar esta boleta",
            "estado": "sin_datos",
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
        items.append({"icono": "⚠️", "titulo": "La suma no cierra",
                      "texto": "Los renglones sumados no dan el total que figura como "
                               "'Total a pagar'. Pedí el desglose antes de pagar."})

    revisiones = sum(1 for i in items if i["icono"] == "⚠️")
    if revisiones == 0:
        estado = "en_orden"
        resumen = (f"Comparamos tu boleta de {_mes(aud.get('mes'))} con las reglas oficiales "
                   "que correspondían en ese momento. No encontramos nada fuera de lugar.")
    else:
        estado = "a_revisar"
        punto = "punto" if revisiones == 1 else "puntos"
        resumen = (f"Comparamos tu boleta de {_mes(aud.get('mes'))} con las reglas oficiales "
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
        "titulo": f"Tu boleta de {_mes(aud.get('mes'))}",
        "estado": estado,
        "resumen": resumen,
        "items": items,
        "acciones": acciones,
        "glosario": glosario,
    }

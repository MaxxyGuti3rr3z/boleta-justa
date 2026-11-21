"""Contrato de datos para análisis con IA.

La boleta PDF NO se envía a ningún lado: este módulo construye el único
payload permitido, con campos tarifarios (sin nombre, dirección, DNI, CUIT,
número de suministro/usuario/factura) y lo valida antes de usarlo.

Uso:
    datos = payload_ia.construir(boleta, auditoria)
    payload_ia.validar(datos)   # lanza ValueError si se filtró algo
    msgs = payload_ia.mensajes(datos, pregunta)
"""
from __future__ import annotations

import json
import re

# Campos permitidos, explícitamente. Todo lo demás se descarta.
PERMITIDOS = {
    "mes", "categoria", "consumo_kwh", "dias_facturados",
    "energia", "impuestos", "otros_cargos", "agua", "totales",
    "auditoria",
}
SUBPERMITIDOS = {
    "energia": {"cargo_fijo", "cargo_consumo", "precio_consumo", "cargo_red",
                "precio_red", "subsidio_nacional", "bonif_tarifa_social", "subtotal"},
    "impuestos": {"tasa_fiscalizacion", "iva_consumidor", "iva_intereses",
                  "percepcion_alumbrado", "subtotal"},
    "otros_cargos": {"fopej", "subtotal"},
    "agua": {"cargo_variable", "cargo_fijo", "iva_punitorio", "iva_moratorio", "subtotal"},
    "totales": {"ejesa", "a_pagar"},
    "auditoria": {"resolucion", "categoria_tabla", "confianza", "cargo_fijo_ok",
                  "uso_red_ok", "uso_red_metodo", "energia_ok", "energia_diff_pct",
                  "bonif_ts_presente", "punitorios_signal", "punitorios_en_vigencia",
                  "estado"},
}

# Patrones que NUNCA deben aparecer en el JSON que sale de este módulo.
PROHIBIDOS = [
    re.compile(r"\b(dni|cuit|cuil|titular|domicilio|direccion|correo|email|telefono)\b", re.I),
    re.compile(r"\b(nombre|apellido|usuario|suministro|nro\s*de\s*cliente)\b", re.I),
    re.compile(r"[\w.+-]+@[\w.-]+\.\w+"),                     # emails
    re.compile(r"(?:\d[\s.-]?){7,}"),                        # números largos (DNI/teléfono/cuenta)
]

SYSTEM_PROMPT = (
    "Respondé en español simple, como a una persona sin conocimientos técnicos. "
    "Usá SOLAMENTE los datos del JSON que te paso. No inventes montos, fechas ni "
    "conclusiones. Si el dato no está en el JSON, decí 'no tengo ese dato'. "
    "No des consejos legales ni afirmes que hay una irregularidad: si algo no "
    "coincide, decí que conviene pedir el desglose a EJESA. "
    "Si el precio de la luz difiere unos pocos puntos del cuadro, explicá que "
    "puede ser la actualización del trimestre (pass through) y que eso solo no "
    "es un error. Mencioná siempre la resolución indicada cuando hables del cuadro."
)


def construir(boleta: dict, auditoria: dict) -> dict:
    """Devuelve SOLO campos tarifarios, con nombres claros y sin comportarse."""
    e = boleta.get("energia", {})
    kwh = None
    if e.get("cargo_consumo") and e.get("precio_consumo"):
        kwh = round(e["cargo_consumo"] / e["precio_consumo"], 1)
    fecha = (boleta.get("fecha_emision") or "").split("/")
    mes = f"{fecha[-1]}-{int(fecha[1]):02d}" if len(fecha) == 3 and fecha[1].isdigit() else None

    datos = {
        "mes": mes,
        "categoria": boleta.get("categoria"),
        "consumo_kwh": kwh,
        "dias_facturados": boleta.get("dias_facturados"),
        "energia": {k: e.get(k) for k in SUBPERMITIDOS["energia"] if e.get(k) is not None},
        "impuestos": {k: boleta.get("impuestos", {}).get(k)
                      for k in SUBPERMITIDOS["impuestos"]
                      if boleta.get("impuestos", {}).get(k) is not None},
        "otros_cargos": {k: boleta.get("otros_cargos", {}).get(k)
                         for k in SUBPERMITIDOS["otros_cargos"]
                         if boleta.get("otros_cargos", {}).get(k) is not None},
        "agua": {k: boleta.get("agua", {}).get(k)
                 for k in SUBPERMITIDOS["agua"]
                 if boleta.get("agua", {}).get(k) is not None},
        "totales": {k: boleta.get("totales", {}).get(k)
                    for k in SUBPERMITIDOS["totales"]
                    if boleta.get("totales", {}).get(k) is not None},
        "auditoria": {k: auditoria.get(k)
                      for k in SUBPERMITIDOS["auditoria"]
                      if auditoria.get(k) is not None},
    }
    validar(datos)
    return datos


def _cadenas(obj):
    """Solo texto: los importes son números y no deben caer en el filtro."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _cadenas(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _cadenas(v)
    elif isinstance(obj, str):
        yield obj


def validar(datos: dict) -> None:
    """Falla si el payload tiene campos o patrones fuera del contrato."""
    if set(datos) - PERMITIDOS:
        raise ValueError(f"campos no permitidos: {sorted(set(datos) - PERMITIDOS)}")
    for clave, valor in datos.items():
        if isinstance(valor, dict):
            extra = set(valor) - SUBPERMITIDOS.get(clave, set())
            if extra:
                raise ValueError(f"campos no permitidos en {clave}: {sorted(extra)}")
    if len(json.dumps(datos, ensure_ascii=False)) > 8000:
        raise ValueError("payload demasiado grande")
    texto = "\n".join(_cadenas(datos))
    for patron in PROHIBIDOS:
        if patron.search(texto):
            raise ValueError("el payload contiene un dato personal posible")


def mensajes(datos: dict, pregunta: str) -> list[dict]:
    """Mensajes listos para un endpoint compatible con chat completions."""
    validar(datos)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Datos de la boleta (JSON):\n" +
         json.dumps(datos, ensure_ascii=False)},
        {"role": "user", "content": "Pregunta: " + pregunta.strip()[:500]},
    ]

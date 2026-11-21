"""Calculadora tarifaria EJESA (T1 residencial) sobre el cuadro oficial publicado.

Fuente de datos: datos/tarifas/res297_2026-08.json (Res. 297-SUSEPU/2026,
Anexo I, Boletín Oficial Nº 106 del 04/09/2026). Stdlib pura, sin dependencias.

Alcance MVP: componentes tarifarios (cargo fijo + uso de red + energía) y
bonificaciones publicadas (Tarifa Social provincial, SEF nacional,
electrodependientes). La capa de impuestos de la boleta se modela en fase 1
con boletas reales. NO emite veredictos legales: muestra el desglose.
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TARIFAS_DEFAULT = RAIZ / "datos" / "tarifas" / "res297_2026-08.json"


def cargar(ruta=None) -> dict:
    return json.loads(Path(ruta or TARIFAS_DEFAULT).read_text(encoding="utf-8"))


def categoria_por_consumo(kwh: float, tarifas: dict) -> dict:
    if kwh < 0:
        raise ValueError("el consumo no puede ser negativo")
    for cat in tarifas["t1_residencial"]["categorias"]:
        if cat["hasta_kwh"] is None or kwh <= cat["hasta_kwh"]:
            return cat
    raise ValueError("consumo fuera de categorías")  # inalcanzable: R7 es abierta


def _bloques(kwh: float, bloques: list, tope: float | None = None) -> float:
    """Descuento total aplicando bloques acumulativos (hasta_kwh por bloque)."""
    total = 0.0
    anterior = 0.0
    restante = min(kwh, tope) if tope is not None else kwh
    for b in bloques:
        tramo = min(restante, b["hasta_kwh"] - anterior)
        if tramo <= 0:
            break
        total += tramo * b["descuento_kwh"]
        restante -= tramo
        anterior = b["hasta_kwh"]
        if restante <= 0:
            break
    return total


def calcular(kwh: float, mes: str = "2026-08", tarifa_social: bool = False,
             sef: bool = False, electrodependiente: bool = False,
             tarifas: dict | None = None) -> dict:
    """Desglose tarifario esperado para un consumo mensual.

    mes: 'YYYY-MM' de la factura. Las bonificaciones solo están cargadas para
    los meses publicados; sin bonificaciones cargadas y con subsidios pedidos,
    se levanta ValueError (no se inventan valores).
    """
    t = tarifas or cargar()
    cat = categoria_por_consumo(kwh, t)
    notas = []

    vig = t["vigencia"]
    if not (vig["desde"][:7] <= mes <= vig["hasta"][:7]):
        notas.append(f"fuera de la vigencia cargada ({vig['desde']} a {vig['hasta']}): "
                     "verificar la resolución del trimestre correspondiente")

    if electrodependiente:
        # los electrodependientes tienen categoría propia RE (no R1-R7)
        re_cat = t["t1_residencial"]["especiales"]["RE"]
        cat = {"id": "RE"}
        fijo = float(re_cat["cargo_fijo"])
        red = kwh * re_cat["uso_red_kwh"]
        energia = kwh * re_cat["energia_plena_kwh"]
    else:
        fijo = float(cat["cargo_fijo"])
        red = kwh * cat["uso_red_kwh"]
        energia = kwh * cat["energia_plena_kwh"]
    d_ts_fijo = d_ts_red = d_sef = 0.0

    bonif = t["bonificaciones"].get(mes)
    if electrodependiente:
        if not bonif:
            raise ValueError(f"sin bonificaciones cargadas para {mes}")
        re = bonif["electrodependientes"]
        d_ts_fijo = min(fijo, re["cargo_fijo_descuento"])
        d_ts_red = kwh * re["uso_red_descuento_kwh"]
        d_sef = kwh * re["energia_descuento_kwh"]
        notas.append("electrodependiente: bonificación total de componentes tarifarios")
    else:
        if tarifa_social or sef:
            if not bonif:
                raise ValueError(f"sin bonificaciones cargadas para {mes}; "
                                 "cargar el anexo de ese mes antes de calcular")
        if tarifa_social and bonif:
            ts = bonif["tarifa_social"]
            if cat["id"] in ts["solo_categorias"]:
                d_ts_fijo = fijo * ts["cargo_fijo_pct"] / 100
            else:
                notas.append("consumo >300 kWh: el anexo publicado solo define "
                             "bonificación de cargo fijo para TS1/TS2 (≤300 kWh); "
                             "verificar aplicación con boleta real")
            d_ts_red = _bloques(kwh, ts["uso_red_bloques"])
        if sef and bonif:
            d_sef = _bloques(kwh, bonif["sef"]["energia_bloques"],
                             tope=bonif["sef"]["bloque_base_kwh"])
            if kwh > bonif["sef"]["bloque_base_kwh"]:
                notas.append(f"consumo por encima del bloque base SEF "
                             f"({bonif['sef']['bloque_base_kwh']} kWh): el excedente "
                             "va a precio pleno")

    subtotal = fijo + red + energia - d_ts_fijo - d_ts_red - d_sef
    return {
        "mes": mes,
        "kwh": kwh,
        "categoria": cat["id"],
        "resolucion": t["resolucion"],
        "cargo_fijo": round(fijo, 2),
        "uso_red_bruto": round(red, 2),
        "energia_bruta": round(energia, 2),
        "descuento_tarifa_social_fijo": round(d_ts_fijo, 2),
        "descuento_tarifa_social_red": round(d_ts_red, 2),
        "descuento_sef_energia": round(d_sef, 2),
        "subtotal_tarifario": round(subtotal, 2),
        "notas": notas + ["subtotal SIN impuestos (IVA, tasas municipales, etc.): "
                          "esa capa se suma en la boleta real"],
    }

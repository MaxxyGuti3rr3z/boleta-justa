r"""Parser de boletas EJESA (fase 1) — procesamiento 100% local.

Extrae SOLO campos tarifarios/facturación; NO guarda nombres, direcciones,
DNI/CUIT, números de suministro, usuario ni factura. Todo lo que se lee de
boletas_reales/ se escribe en boletas_reales/_parseado/ (gitignoreado).

Uso: venv\Scripts\python.exe src\parser_boletas.py
"""
import json
import re
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
BOLETAS = RAIZ / "boletas_reales"
SALIDA = BOLETAS / "_parseado"

IMPORTE = re.compile(r"-?\d[\d.]*,\d{1,2}")
NUMERO = re.compile(r"\d[\d.,]*")
FECHA = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")


def a_float(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if "," in s:
        # importes en la boleta: coma decimal, punto de miles ("4.772,00")
        return float(s.replace(".", "").replace(",", "."))
    # precios unitarios con punto decimal ("156.1556 $/kWh")
    try:
        return float(s)
    except ValueError:
        return None


def importe_en(linea: str) -> float | None:
    m = IMPORTE.search(linea)
    return a_float(m.group()) if m else None


def precio_kwh(linea: str) -> float | None:
    m = re.search(r"\(\s*([\d.,]+)\s*\$/kWh\s*\)", linea)
    return a_float(m.group(1)) if m else None


def extraer_lineas(pdf: Path) -> list[str]:
    lector = PdfReader(str(pdf))
    return [l.strip() for p in lector.pages
            for l in (p.extract_text() or "").splitlines() if l.strip()]


def parsear(lineas: list[str]) -> dict:
    """Parsea líneas de texto a un dict SOLO con campos de facturación."""
    r = {
        "periodo": None, "fecha_emision": None, "vencimiento": None,
        "categoria": None, "dias_facturados": None, "consumo_diario": None,
        "diferencia_medidor": [],
        "energia": {}, "impuestos": {}, "otros_cargos": {}, "agua": {},
        "totales": {}, "punitorios_detectados": False, "notas": [],
    }
    seccion = "cabecera"
    en_agua = False
    esperando = None  # etiqueta de fecha que va en la línea siguiente

    for i, linea in enumerate(lineas):
        up = linea.upper()

        if esperando:
            if esperando == "fecha_emision" and FECHA.search(linea):
                r["fecha_emision"] = FECHA.search(linea).group()
            elif esperando == "vencimiento" and FECHA.search(linea):
                r["vencimiento"] = FECHA.search(linea).group()
            esperando = None

        # cambios de sección
        if up.startswith("EVOLUCIÓN DEL CONSUMO EN KWH"):
            seccion = "consumo"
        elif up.startswith("ENERGÍA ELÉCTRICA"):
            seccion = "energia"
        elif up.startswith("TASAS E IMPUESTOS"):
            seccion = "tasas_agua" if en_agua else "impuestos"
        elif up.startswith("OTROS CARGOS"):
            seccion = "otros"
        elif up.startswith("TOTAL EJESA"):
            r["totales"]["ejesa"] = importe_en(linea)
            seccion = "entre_totales"
        elif "SERVICIOS SANITARIOS" in up:
            seccion = "agua"
            en_agua = True
        elif up.startswith("TOTAL A PAGAR"):
            # el importe puede estar unas líneas más abajo, no siempre inmediato
            for sig in lineas[i + 1:i + 5]:
                v = importe_en(sig)
                if v is not None:
                    r["totales"]["a_pagar"] = v
                    break
        elif up.startswith("PERÍODO") or up.startswith("PERIODO"):
            if i + 1 < len(lineas) and FECHA.search(lineas[i + 1]):
                r["periodo"] = FECHA.search(lineas[i + 1]).group()

        # etiqueta → valor en la línea siguiente
        if up == "FECHA DE EMISIÓN" or up == "FECHA DE EMISION":
            esperando = "fecha_emision"
        if up == "VENCIMIENTO":
            esperando = "vencimiento"

        # consumo
        if "CONSUMO DIARIO" in up:
            nums = NUMERO.findall(linea)
            if nums:
                r["consumo_diario"] = a_float(nums[0])
        if "DÍAS FACTURADOS" in up or "DIAS FACTURADOS" in up:
            nums = NUMERO.findall(linea)
            if nums:
                r["dias_facturados"] = a_float(nums[0])

        # categoría tarifaria en la tabla del medidor (ej. T1TS)
        m = re.search(r"\bT\d+[A-Z]{0,4}\b", linea)
        if m and ("ANTERIOR" in up or "ACTUAL" in up):
            r["categoria"] = m.group()
        if up.startswith("DIFERENCIA"):
            r["diferencia_medidor"] = [a_float(n) for n in NUMERO.findall(linea)]

        # cargos por sección (etiquetas exactas observadas en boletas reales)
        v = importe_en(linea)
        if v is None:
            continue
        if seccion == "energia":
            if up.startswith("CARGO FIJO"):
                r["energia"].setdefault("cargo_fijo", v)
            elif up.startswith("CARGO POR CONSUMO DE ENERGÍA"):
                r["energia"]["cargo_consumo"] = v
                r["energia"]["precio_consumo"] = precio_kwh(linea)
            elif up.startswith("CARGO POR USO DE RED"):
                r["energia"]["cargo_red"] = v
                r["energia"]["precio_red"] = precio_kwh(linea)
            elif up.startswith("SUBSIDIO ESTADO NACIONAL"):
                r["energia"]["subsidio_nacional"] = v
            elif up.startswith("BONIF. TARIFA SOCIAL"):
                r["energia"]["bonif_tarifa_social"] = v
            elif up.startswith("SUBTOTAL ENERGÍA"):
                r["energia"]["subtotal"] = v
        elif seccion == "impuestos":
            if up.startswith("TASA FISCALIZACIÓN") and ("SUPEPU" in up or "SUSEPU" in up):
                # la línea trae "%" con coma decimal antes del importe: tomar el ÚLTIMO
                importes = IMPORTE.findall(linea)
                r["impuestos"]["tasa_fiscalizacion"] = a_float(importes[-1]) if importes else v
                porc = re.search(r"([\d.,]+)\s*%", linea)
                r["impuestos"]["tasa_fiscalizacion_pct"] = a_float(porc.group(1)) if porc else None
            elif up.startswith("IVA CONSUMIDOR FINAL"):
                r["impuestos"]["iva_consumidor"] = v
            elif "IVA INTERESES" in up:
                r["impuestos"]["iva_intereses"] = v
            elif up.startswith("PERCEPC."):
                r["impuestos"]["percepcion"] = v
            elif up.startswith("PERCEP.ALUMBRADO") or "ALUMBRADO PUBLICO" in up:
                r["impuestos"]["percepcion_alumbrado"] = v
            elif up.startswith("SUBTOTAL TASAS"):
                r["impuestos"]["subtotal"] = v
        elif seccion == "otros":
            if up.startswith("CARGO FOPEJ"):
                r["otros_cargos"]["fopej"] = v
            elif up.startswith("AJUSTE"):
                r["otros_cargos"].setdefault("ajustes", []).append(v)
            elif up.startswith("SUBTOTAL OTROS"):
                r["otros_cargos"]["subtotal"] = v
        elif seccion in ("agua", "tasas_agua"):
            if up.startswith("CARGO VARIABLE AGUA"):
                r["agua"]["cargo_variable"] = v
            elif up.startswith("CARGO FIJO"):
                r["agua"].setdefault("cargo_fijo", v)
            elif up.startswith("IVA INTERÉS PUNITORIO") or up.startswith("IVA INTERES PUNITORIO"):
                r["agua"]["iva_punitorio"] = v
                if v and v > 0:
                    r["punitorios_detectados"] = True
            elif "IVA INTERÉS MORATORIO" in up or "IVA INTERES MORATORIO" in up:
                r["agua"]["iva_moratorio"] = v
            elif up.startswith("IVA") and "%" in linea:
                r["agua"].setdefault("iva", v)
            elif up.startswith("SUBTOTAL SERVICIOS SANITARIOS"):
                r["agua"]["subtotal"] = v
            elif up.startswith("SUBTOTAL TASAS"):
                r["agua"]["subtotal_impuestos"] = v
            elif up.startswith("TOTAL"):
                r["agua"]["total"] = v
    # consistencia aritmética básica (sin exponer importes en la consola)
    agua_total = r["agua"].get("subtotal")
    if agua_total is None:
        agua_total = r["agua"].get("total")
    subs = [r["energia"].get("subtotal"), r["impuestos"].get("subtotal"),
            r["otros_cargos"].get("subtotal"), agua_total]
    if all(x is not None for x in subs):
        r["consistencia"] = {
            "suma_subtotales": round(sum(subs), 2),
            "total_ejesa": r["totales"].get("ejesa"),
            "total_a_pagar": r["totales"].get("a_pagar"),
            "coincide_a_pagar": (r["totales"].get("a_pagar") is not None and
                                 abs(sum(subs) - r["totales"]["a_pagar"]) < 1),
        }
    return r


def main() -> None:
    if not BOLETAS.exists():
        print("No existe boletas_reales/")
        return
    pdfs = sorted({p.resolve() for p in BOLETAS.glob("*.pdf")})
    if not pdfs:
        print("No hay PDFs en boletas_reales/")
        return
    SALIDA.mkdir(exist_ok=True)
    for i, pdf in enumerate(pdfs, 1):
        try:
            r = parsear(extraer_lineas(pdf))
        except Exception as e:
            print(f"Boleta {i}: error local ({type(e).__name__})")
            continue
        (SALIDA / f"boleta_{i}.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        e = r["energia"]
        print(f"Boleta {i}: categoría={r['categoria']} | período={r['periodo']} "
              f"| cargo fijo={'OK' if e.get('cargo_fijo') is not None else 'FALTA'} "
              f"| consumo={'OK' if e.get('cargo_consumo') is not None else 'FALTA'} "
              f"| red={'OK' if e.get('cargo_red') is not None else 'FALTA'} "
              f"| impuestos={'OK' if r['impuestos'].get('subtotal') is not None else 'FALTA'} "
              f"| agua={'OK' if r['agua'].get('subtotal') is not None else 'FALTA'} "
              f"| punitorios={'SÍ' if r['punitorios_detectados'] else 'no'}")
    print(f"\nJSONs locales (sin datos personales) en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()

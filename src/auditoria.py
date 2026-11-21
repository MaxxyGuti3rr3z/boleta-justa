r"""Auditoría local: cada boleta contra el cuadro tarifario de su trimestre.

No imprime importes ni datos personales: solo resultados (OK / DIFIERE / %)
para que el usuario audite en su máquina. El informe detallado queda en
boletas_reales/_parseado/auditoria.json (gitignoreado).

Uso: venv\Scripts\python.exe src\auditoria.py
"""
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TABLAS_DIR = RAIZ / "datos" / "tarifas"
PARSEADAS = RAIZ / "boletas_reales" / "_parseado"


def cargar_tablas() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(TABLAS_DIR.glob("*.json"))]


def mes_de(fecha: str | None) -> str | None:
    """'DD/MM/YYYY' → 'YYYY-MM' (mes de emisión, proxy del período facturado)."""
    if not fecha:
        return None
    partes = fecha.split("/")
    if len(partes) != 3:
        return None
    return f"{partes[2]}-{partes[1]}"


def tabla_para(mes: str | None, tablas: list[dict]) -> dict | None:
    if not mes:
        return None
    for t in tablas:
        if t["vigencia"]["desde"][:7] <= mes <= t["vigencia"]["hasta"][:7]:
            return t
    return None


def seleccionar_tabla(boleta: dict, tablas: list[dict]) -> tuple[dict | None, float, str]:
    """Elige el cuadro por coincidencia empírica de los componentes VAD
    (cargo fijo + uso de red), que son estables dentro del trimestre.
    La fecha de emisión NO es confiable: varias boletas se facturan por
    períodos anteriores. Devuelve (tabla, score %, confianza)."""
    e = boleta.get("energia", {})
    if e.get("cargo_fijo") is None and e.get("precio_red") is None:
        return None, 0.0, "sin datos"
    mejor = None
    for t in tablas:
        cats = t["t1_residencial"]["categorias"]
        diffs = []
        for clave, valor in (("cargo_fijo", e.get("cargo_fijo")),
                             ("uso_red_kwh", e.get("precio_red"))):
            if valor is None:
                continue
            c = min(cats, key=lambda x: abs(x[clave] - valor) / max(x[clave], 1))
            diffs.append(abs(100 * (valor - c[clave]) / c[clave]))
        if not diffs:
            continue
        score = sum(diffs) / len(diffs)
        if mejor is None or score < mejor[1]:
            mejor = (t, score)
    if mejor is None:
        return None, 0.0, "sin cuadros"
    confianza = "alta" if mejor[1] < 0.5 else ("media" if mejor[1] < 3 else "baja")
    return mejor[0], round(mejor[1], 2), confianza


def _cercana(cats: list[dict], clave: str, valor: float | None, tol_pct=0.3) -> dict | None:
    if valor is None:
        return None
    for c in cats:
        base = abs(c[clave]) or 1
        if abs(c[clave] - valor) <= max(base * tol_pct / 100, 0.01):
            return c
    return None


def auditar(boleta: dict, tablas: list[dict]) -> dict:
    mes = mes_de(boleta.get("fecha_emision"))
    tabla, score, confianza = seleccionar_tabla(boleta, tablas)
    tabla_fecha = tabla_para(mes, tablas)
    base = {"mes": mes, "categoria_boleta": boleta.get("categoria"),
            "confianza": confianza, "score_vad_pct": score}
    if not tabla:
        return {**base, "estado": "sin_cuadro_cargado", "resolucion": None}
    cats = tabla["t1_residencial"]["categorias"]
    e = boleta.get("energia", {})
    cat_fijo = _cercana(cats, "cargo_fijo", e.get("cargo_fijo"))
    cat_red = _cercana(cats, "uso_red_kwh", e.get("precio_red"))
    cat_energia = _cercana(cats, "energia_plena_kwh", e.get("precio_consumo"))

    cat = cat_fijo or cat_red or cat_energia
    diff_energia = 0.0
    if cat and e.get("precio_consumo") and cat["energia_plena_kwh"]:
        diff_energia = round(100 * (e["precio_consumo"] - cat["energia_plena_kwh"]) /
                             cat["energia_plena_kwh"], 1)

    return {
        **base,
        "estado": "auditada",
        "resolucion": tabla["resolucion"],
        "resolucion_por_fecha": tabla_fecha["resolucion"] if tabla_fecha else None,
        "categoria_tabla": cat["id"] if cat else None,
        "cargo_fijo_ok": cat_fijo is not None,
        "uso_red_ok": cat_red is not None,
        "energia_ok": cat_energia is not None,
        "energia_diff_pct": diff_energia if not cat_energia else 0.0,
        "nota": tabla.get("nota_pass_through", ""),
        "punitorios_signal": boleta.get("punitorios_detectados", False),
    }


def main() -> None:
    tablas = cargar_tablas()
    archivos = [p for p in sorted(PARSEADAS.glob("*.json")) if p.name != "auditoria.json"]
    if not archivos:
        print("No hay boletas parseadas en boletas_reales/_parseado/")
        return
    resultados = []
    for i, archivo in enumerate(archivos, 1):
        if archivo.name == "auditoria.json":
            continue
        boleta = json.loads(archivo.read_text(encoding="utf-8"))
        r = {"boleta": i, **auditar(boleta, tablas)}
        resultados.append(r)
        if r["estado"] != "auditada":
            print(f"Boleta {i} ({r['mes']}): SIN CUADRO CARGADO para ese trimestre")
            continue
        energia_txt = "OK" if r["energia_ok"] else f"DIFIERE {r['energia_diff_pct']:+}%"
        aviso = ""
        if r.get("resolucion_por_fecha") and r["resolucion_por_fecha"] != r["resolucion"]:
            aviso = f" [por fecha sería {r['resolucion_por_fecha']}: revisar período]"
        print(f"Boleta {i} ({r['mes']}) · {r['resolucion']} (confianza {r['confianza']}, "
              f"VAD {r['score_vad_pct']}%) · cat {r['categoria_tabla'] or '?'}: "
              f"fijo={'OK' if r['cargo_fijo_ok'] else 'DIFIERE'} "
              f"red={'OK' if r['uso_red_ok'] else 'DIFIERE'} "
              f"energía={energia_txt} "
              f"· punitorios={'SEÑAL' if r['punitorios_signal'] else 'no'}{aviso}")
    (PARSEADAS / "auditoria.json").write_text(
        json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nInforme local (sin datos personales): boletas_reales/_parseado/auditoria.json")


if __name__ == "__main__":
    main()

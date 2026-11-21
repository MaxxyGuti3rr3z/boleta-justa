"""API local de Boleta Justa: simulador tarifario + verificador del decreto.

Uso:  python src/api.py  → http://127.0.0.1:8101
(venv: venv\Scripts\python.exe src\api.py)
"""
import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from . import tarifas, decreto, auditoria
except ImportError:  # ejecución directa: python src/api.py
    import tarifas
    import decreto
    import auditoria

RAIZ = Path(__file__).resolve().parent.parent

app = FastAPI(title="Boleta Justa", version="0.2.0")
CUADRO = tarifas.cargar()


class CalculoIn(BaseModel):
    kwh: float
    mes: str = "2026-08"
    tarifa_social: bool = False
    sef: bool = False
    electrodependiente: bool = False


class CorteIn(BaseModel):
    vencimiento_segunda_impaga: date
    fecha_corte: date


class RetiroIn(BaseModel):
    fecha_corte: date
    fecha_retiro: date


class PunitoriosIn(BaseModel):
    monto_punitorios: float
    fecha_factura: date


@app.get("/api/cuadro")
def cuadro():
    return {
        "resolucion": CUADRO["resolucion"],
        "publicacion": CUADRO["publicacion"],
        "fuente": CUADRO["fuente"],
        "vigencia": CUADRO["vigencia"],
        "categorias": CUADRO["t1_residencial"]["categorias"],
        "meses_bonificaciones": [m for m in CUADRO["bonificaciones"] if m != "nota"],
        "nota_pass_through": CUADRO["nota_pass_through"],
    }


@app.post("/api/calcular")
def calcular(c: CalculoIn):
    try:
        con = tarifas.calcular(c.kwh, mes=c.mes, tarifa_social=c.tarifa_social,
                               sef=c.sef, electrodependiente=c.electrodependiente,
                               tarifas=CUADRO)
        pleno = tarifas.calcular(c.kwh, mes=c.mes, tarifas=CUADRO)
    except ValueError as e:
        raise HTTPException(422, str(e))
    ahorro = pleno["subtotal_tarifario"] - con["subtotal_tarifario"]
    pct = round(100 * ahorro / pleno["subtotal_tarifario"], 1) if pleno["subtotal_tarifario"] else 0
    return {"desglose": con, "sin_subsidios": pleno["subtotal_tarifario"],
            "ahorro": round(ahorro, 2), "ahorro_pct": pct}


@app.post("/api/verificar/corte")
def verificar_corte(c: CorteIn):
    try:
        return decreto.verificar_corte(c.vencimiento_segunda_impaga, c.fecha_corte)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/verificar/retiro")
def verificar_retiro(r: RetiroIn):
    try:
        return decreto.verificar_retiro_medidor(r.fecha_corte, r.fecha_retiro)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/verificar/punitorios")
def verificar_punitorios(p: PunitoriosIn):
    try:
        return decreto.verificar_punitorios(p.monto_punitorios, p.fecha_factura)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/auditoria")
def ver_auditoria():
    """Auditoría de las boletas parseadas localmente. SOLO campos tarifarios:
    nunca devuelve nombres, direcciones, DNI ni números de cuenta/factura."""
    carpeta = RAIZ / "boletas_reales" / "_parseado"
    archivos = sorted(carpeta.glob("boleta_*.json")) if carpeta.exists() else []
    tablas = auditoria.cargar_tablas()
    return [
        {"boleta": i, **auditoria.auditar(json.loads(p.read_text(encoding="utf-8")), tablas)}
        for i, p in enumerate(archivos, 1)
    ]


app.mount("/", StaticFiles(directory=RAIZ / "web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8101)

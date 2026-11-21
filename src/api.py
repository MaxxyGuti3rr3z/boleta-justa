"""API local de Boleta Justa: simulador tarifario + verificador del decreto.

Uso:  python src/api.py  → http://127.0.0.1:8101
(venv: venv\Scripts\python.exe src\api.py)
"""
from tempfile import TemporaryDirectory

import json
import os
from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader

try:
    from . import tarifas, decreto, auditoria, parser_boletas, explicar, config, payload_ia, preguntas, ia_client
except ImportError:  # ejecución directa: python src/api.py
    import tarifas
    import decreto
    import auditoria
    import parser_boletas
    import explicar
    import config
    import payload_ia
    import preguntas
    import ia_client

RAIZ = Path(__file__).resolve().parent.parent

app = FastAPI(title="Boleta Justa", version="0.2.0")
CUADRO = tarifas.cargar()


@app.get("/api/config")
def ver_config():
    return {"modo_publico": config.PUBLICO, "max_paginas": config.MAX_PAGINAS,
            "consentimiento": config.consentimiento()}


@app.get("/api/health")
def salud():
    return {"ok": True, "modo": "publico" if config.PUBLICO else "local"}


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


@app.post("/api/auditar")
async def auditar_pdf(request: Request, file: UploadFile = File(...)):
    """Recibe un PDF de boleta, lo analiza en memoria local y devuelve SOLO
    la explicación en lenguaje llano. No guarda el archivo ni datos personales."""
    # Detrás de un proxy, X-Forwarded-For identifica a cada persona; si no hay
    # proxy, el platform igual suele setearlo. Si se expone directo, se puede
    # falsear: en ese caso limitar en el reverse proxy.
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else "desconocida"))
    if config.PUBLICO and not config.limitador.permite(ip):
        raise HTTPException(429, "Demasiadas boletas seguidas. Esperá un minuto.")
    nombre = (file.filename or "").lower()
    if not nombre.endswith(".pdf"):
        raise HTTPException(415, "Solo se aceptan archivos PDF")
    datos = await file.read()
    if not datos or len(datos) > 12_000_000:
        raise HTTPException(413, "El PDF debe pesar menos de 12 MB")
    # TemporaryDirectory: en Windows un NamedTemporaryFile abierto no se puede
    # reabrir con pypdf. Se borra todo al salir, incluido el PDF del usuario.
    with TemporaryDirectory() as carpeta:
        pdf = Path(carpeta) / "boleta.pdf"
        pdf.write_bytes(datos)
        try:
            paginas = len(PdfReader(str(pdf)).pages)
            if paginas > config.MAX_PAGINAS:
                raise HTTPException(413, "El PDF tiene demasiadas páginas")
            boleta = parser_boletas.parsear(parser_boletas.extraer_lineas(pdf))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(422, "No pudimos leer el PDF. ¿Es una boleta de EJESA?")
    # acá ya no queda ningún archivo del usuario en disco
    resultado = auditoria.auditar(boleta, auditoria.cargar_tablas())
    datos = payload_ia.construir(boleta, resultado)
    return {"auditoria": resultado,
            "explicacion": explicar.explicar(resultado, boleta),
            "payload": datos}


class PreguntaIn(BaseModel):
    pregunta: str
    payload: dict


@app.post("/api/preguntar")
def preguntar(p: PreguntaIn):
    """Responde sobre la boleta. El payload ya viene sin datos personales:
    el PDF nunca se envía, y si hay IA configurada recibe SOLO ese JSON."""
    try:
        payload_ia.validar(p.payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if not p.pregunta.strip():
        raise HTTPException(422, "Escribí una pregunta")
    local = preguntas.responder(p.pregunta, p.payload, p.payload.get("auditoria", {}))
    if ia_client.configurada():
        try:
            texto = ia_client.consultar(payload_ia.mensajes(p.payload, p.pregunta))
            if texto:
                return {**local, "respuesta": texto, "modo": "ia", "payload": p.payload}
        except Exception:
            pass  # fallback a respuesta local, sin logs con datos
    return {**local, "payload": p.payload}


@app.get("/api/auditoria")
def ver_auditoria():
    """Auditoría de las boletas parseadas localmente. SOLO campos tarifarios:
    nunca devuelve nombres, direcciones, DNI ni números de cuenta/factura.
    En modo público se desactiva: son las boletas del dueño del proyecto."""
    if config.PUBLICO:
        raise HTTPException(404, "No disponible en la versión pública")
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
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8101")))

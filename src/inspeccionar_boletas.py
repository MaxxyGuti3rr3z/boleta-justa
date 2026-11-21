r"""Inspección SEGURA de boletas reales (fase 1).

Lee SOLO PDFs de boletas_reales/, guarda el texto extraído en
boletas_reales/_texto/ (también gitignoreado) y muestra por consola ÚNICAMENTE
líneas relacionadas con cargos/consumo/impuestos, con todos los números
enmascarados (#). Nunca imprime nombres, direcciones, emails, teléfonos ni
importes: la consola sirve para ver la ESTRUCTURA del documento, no los datos.

Uso: venv\Scripts\python.exe src\inspeccionar_boletas.py
"""
import re
from pathlib import Path

from pypdf import PdfReader

RAIZ = Path(__file__).resolve().parent.parent
BOLETAS = RAIZ / "boletas_reales"
SALIDA = BOLETAS / "_texto"
CLAVES = (
    "cargo", "consumo", "energ", "red", "iva", "impuesto", "tasa", "total",
    "factura", "periodo", "vencimiento", "medidor", "suministro", "tarifa",
    "subsidio", "bonific", "saldo", "kwh", "fondo", "importe", "monto",
    "derecho", "rehabilit", "suspension", "descuento", "adeudado",
)


def enmascarar(linea: str) -> str:
    """Reemplaza números, emails y posibles identificadores por #, sin borrar etiquetas."""
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", linea)
    s = re.sub(r"\b\d[\d.,/\-]*\d\b|\b\d+\b", lambda m: "#" * len(m.group()), s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    if not BOLETAS.exists():
        print("No existe boletas_reales/")
        return
    SALIDA.mkdir(exist_ok=True)
    pdfs = sorted({p.resolve() for p in BOLETAS.glob("*.pdf")})
    if not pdfs:
        print("No hay PDFs en boletas_reales/")
        return
    print(f"{len(pdfs)} PDF(s) encontrado(s). Procesamiento local, sin envíos a terceros.\n")

    for i, ruta in enumerate(pdfs, 1):
        try:
            lector = PdfReader(str(ruta))
            paginas = []
            for pagina in lector.pages:
                paginas.append(pagina.extract_text() or "")
            texto = "\n".join(paginas)
        except Exception as e:  # no mostrar ruta: puede contener datos personales
            print(f"Boleta {i}: ERROR al leer PDF ({type(e).__name__})")
            continue

        # El texto crudo queda solo en disco local, con nombre anónimo
        destino = SALIDA / f"boleta_{i}.txt"
        destino.write_text(texto, encoding="utf-8")

        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
        utiles = [l for l in lineas if any(p in l.lower() for p in CLAVES)]
        print(f"Boleta {i}: {len(paginas)} página(s), {len(texto)} caracteres, "
              f"{len(lineas)} líneas ({len(utiles)} con palabras clave)")
        for l in utiles[:70]:
            print("   ", enmascarar(l)[:130])
        if len(utiles) > 70:
            print(f"    ... y {len(utiles) - 70} líneas más (ver {destino.name})")
        print()


if __name__ == "__main__":
    main()

"""Verificador de plazos del Decreto Acuerdo 5658-JG/2026 (emergencia energética
y tarifaria de Jujuy, BO Nº 86 del 24/07/2026, vigente hasta el 31/12/2027).

Art. 3, usuarios T1 (<15 kW), cita textual:
  A. "SUSPENDER los cortes de suministro de energía eléctrica por falta de pago,
     el que podrá efectivizarse recién después de los veinte (20) días corridos
     de mora de la segunda factura consecutiva impaga."
  B. "SUSPENDER el retiro del medidor del servicio de energía, el que podrá
     llevarse adelante una vez cumplidos sesenta (60) días posteriores del
     corte del suministro."
  C. "PROHIBIR el cobro de los intereses punitorios que se puedan generar
     durante la vigencia del presente decreto acuerdo..."

Interpretación de los plazos (literal del texto):
  - Corte: "después de los 20 días" → habilitado desde el día 21. El día exacto
    20 se marca como zona gris de interpretación (no se afirma legalidad).
  - Retiro de medidor: "una vez cumplidos 60 días" → habilitado desde el día 60.

Esta herramienta NO emite veredictos legales: calcula plazos, muestra el estado
y cita la normativa para que el usuario arme su reclamo.
"""
from datetime import date

DECRETO = "5658-JG/2026"
VIGENCIA_DESDE = date(2026, 7, 20)
VIGENCIA_HASTA = date(2027, 12, 31)
DIAS_MORA_CORTE = 20
DIAS_RETIRO_MEDIDOR = 60

CITA_CORTE = ("Art. 3.A: el corte por falta de pago podrá efectivizarse recién "
              "después de los veinte (20) días corridos de mora de la segunda "
              "factura consecutiva impaga.")
CITA_RETIRO = ("Art. 3.B: el retiro del medidor podrá llevarse adelante una vez "
               "cumplidos sesenta (60) días posteriores del corte del suministro.")
CITA_PUNITORIOS = ("Art. 3.C: prohibido el cobro de intereses punitorios durante "
                   "la vigencia del decreto (también Agua Potable para consumos "
                   "≤30 m³/mes, Art. 7).")


def _en_vigencia(fecha: date) -> bool:
    return VIGENCIA_DESDE <= fecha <= VIGENCIA_HASTA


def verificar_corte(vencimiento_segunda_impaga: date, fecha_corte: date) -> dict:
    """¿El corte respetó los 20 días de mora de la segunda factura impaga?"""
    if fecha_corte < vencimiento_segunda_impaga:
        raise ValueError("la fecha de corte no puede ser anterior al vencimiento")
    dias = (fecha_corte - vencimiento_segunda_impaga).days
    notas = []
    if not _en_vigencia(fecha_corte):
        notas.append(f"el corte ({fecha_corte}) está fuera de la vigencia del "
                     f"decreto ({VIGENCIA_DESDE} a {VIGENCIA_HASTA}): aplicar la "
                     "normativa vigente en esa fecha")
    if dias < DIAS_MORA_CORTE:
        estado = "anticipado"
        notas.append(f"corte a los {dias} días de mora: el decreto exige más de "
                     f"{DIAS_MORA_CORTE} días corridos desde el vencimiento de la "
                     "segunda factura consecutiva impaga")
    elif dias == DIAS_MORA_CORTE:
        estado = "zona_gris"
        notas.append("corte en el día exacto 20: el texto dice 'después de los "
                     "veinte días'; hay zona gris de interpretación, consultar "
                     "antes de afirmar incumplimiento")
    else:
        estado = "plazo_cumplido"
    return {
        "decreto": DECRETO,
        "dias_mora_al_corte": dias,
        "estado": estado,
        "normativa": CITA_CORTE,
        "notas": notas,
    }


def verificar_retiro_medidor(fecha_corte: date, fecha_retiro: date) -> dict:
    """¿El retiro del medidor respetó los 60 días posteriores al corte?"""
    if fecha_retiro < fecha_corte:
        raise ValueError("la fecha de retiro no puede ser anterior al corte")
    dias = (fecha_retiro - fecha_corte).days
    notas = []
    if not _en_vigencia(fecha_retiro):
        notas.append("el retiro está fuera de la vigencia del decreto: aplicar "
                     "la normativa vigente en esa fecha")
    if dias < DIAS_RETIRO_MEDIDOR:
        estado = "anticipado"
        notas.append(f"retiro a los {dias} días del corte: el decreto exige "
                     f"{DIAS_RETIRO_MEDIDOR} días cumplidos")
    else:
        estado = "plazo_cumplido"
    return {
        "decreto": DECRETO,
        "dias_desde_corte": dias,
        "estado": estado,
        "normativa": CITA_RETIRO,
        "notas": notas,
    }


def verificar_punitorios(monto_punitorios: float, fecha_factura: date) -> dict:
    """Intereses punitorios en una factura dentro de la vigencia → prohibidos."""
    if monto_punitorios < 0:
        raise ValueError("el monto no puede ser negativo")
    if not _en_vigencia(fecha_factura):
        return {"decreto": DECRETO, "estado": "fuera_de_vigencia",
                "normativa": CITA_PUNITORIOS,
                "notas": ["factura fuera de la vigencia del decreto"]}
    if monto_punitorios > 0:
        return {"decreto": DECRETO, "estado": "prohibido_cobrado",
                "monto": monto_punitorios, "normativa": CITA_PUNITORIOS,
                "notas": [f"la factura incluye ${monto_punitorios:,.2f} de intereses "
                          "punitorios, prohibidos por el Art. 3.C durante la emergencia"]}
    return {"decreto": DECRETO, "estado": "sin_punitorios",
            "normativa": CITA_PUNITORIOS, "notas": []}

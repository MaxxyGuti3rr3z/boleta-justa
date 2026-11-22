"""Configuración del despliegue público (modo local = privacidad estricta)."""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque

PUBLICO = os.getenv("MODO_PUBLICO", "").strip().lower() in ("1", "true", "yes")
AUTH = os.getenv("AUTH_HABILITADO", "").strip().lower() in ("1", "true", "yes")
AUTH_DB = os.getenv("AUTH_DB", "datos/auth.db")
MAX_HISTORIAL = int(os.getenv("MAX_HISTORIAL", "50"))
DIAS_RETENCION = int(os.getenv("DIAS_RETENCION_HISTORIAL", "90"))
MAX_PAGINAS = int(os.getenv("MAX_PAGINAS_BOLETA", "40"))
RATE_MAX = int(os.getenv("RATE_MAX", "20"))          # PDFs por ventana
RATE_VENTANA = int(os.getenv("RATE_VENTANA", "60"))  # segundos

CONSENTIMIENTO_LOCAL = (
    "Elegí el PDF de tu boleta de EJESA. Lo analizamos acá nomás, en tu "
    "computadora: no se sube a ningún servidor, no se guarda y nunca "
    "mostramos tus datos personales."
)
CONSENTIMIENTO_PUBLICO = (
    "Elegí el PDF de tu boleta de EJESA. Tu archivo se envía a este servidor "
    "solo para analizarlo: no se guarda, no se comparte y no se muestra. "
    "Si preferís que no salga de tu dispositivo, descargá el proyecto y usalo en local."
)


def consentimiento() -> str:
    return CONSENTIMIENTO_PUBLICO if PUBLICO else CONSENTIMIENTO_LOCAL


class Limitador:
    """Ventana deslizante simple, en memoria por proceso."""

    def __init__(self, maximo: int = RATE_MAX, ventana: int = RATE_VENTANA):
        self.maximo = maximo
        self.ventana = ventana
        self._eventos: dict[str, deque[float]] = defaultdict(deque)

    def permite(self, clave: str, ahora: float | None = None) -> bool:
        ahora = time.monotonic() if ahora is None else ahora
        cola = self._eventos[clave]
        while cola and ahora - cola[0] >= self.ventana:
            cola.popleft()
        if len(cola) >= self.maximo:
            return False
        cola.append(ahora)
        return True


limitador = Limitador()

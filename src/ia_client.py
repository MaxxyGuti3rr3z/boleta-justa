"""Cliente opcional de IA: SOLO se llama si el usuario configura un endpoint.

Nunca se envía el PDF: `payload_ia` garantiza que viajen únicamente campos
tarifarios. Sin configuración, devuelve None y la app responde en local.
"""
from __future__ import annotations

import json
import os
import urllib.request

URL = os.getenv("IA_API_URL", "").strip()
KEY = os.getenv("IA_API_KEY", "").strip()
MODELO = os.getenv("IA_MODELO", "gpt-4o-mini").strip()


def configurada() -> bool:
    return bool(URL and KEY)


def consultar(mensajes: list[dict]) -> str | None:
    """Endpoint compatible con chat completions. Sin logs de contenido."""
    if not configurada():
        return None
    cuerpo = json.dumps({"model": MODELO, "messages": mensajes,
                         "temperature": 0.2, "max_tokens": 600}).encode("utf-8")
    req = urllib.request.Request(
        URL, data=cuerpo,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        datos = json.load(resp)
    return datos["choices"][0]["message"]["content"].strip()

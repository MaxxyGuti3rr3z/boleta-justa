#!/usr/bin/env python3
"""Genera versión de cuadros + íconos PWA. No editar los archivos de salida a mano."""
import hashlib
import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "datos" / "tarifas"
CLIENTE = RAIZ / "cliente"
ICONOS = CLIENTE / "icons"

archivos = sorted(p for p in TABLAS.glob("*.json") if not p.name.startswith("_"))
contenido = b"".join(p.read_bytes() for p in archivos)
hash_cuadros = hashlib.sha256(contenido).hexdigest()[:12]
actualizado = date.fromtimestamp(max(p.stat().st_mtime for p in archivos)).isoformat()
resoluciones = [json.loads(p.read_text(encoding="utf-8"))["resolucion"] for p in archivos]

version = {
    "cache": f"boleta-justa-{hash_cuadros}",
    "cuadros_hash": hash_cuadros,
    "actualizado": actualizado,
    "resoluciones": resoluciones,
}
(CLIENTE / "version.json").write_text(
    json.dumps(version, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

ICONOS.mkdir(exist_ok=True)
for tam in (192, 512):
    img = Image.new("RGBA", (tam, tam), (12, 14, 18, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([tam * 0.06, tam * 0.06, tam * 0.94, tam * 0.94],
                        radius=tam * 0.18, fill=(20, 23, 29, 255),
                        outline=(255, 194, 51, 255), width=max(2, tam // 64))
    rayo = [
        (tam * 0.56, tam * 0.16), (tam * 0.30, tam * 0.55),
        (tam * 0.48, tam * 0.55), (tam * 0.40, tam * 0.86),
        (tam * 0.72, tam * 0.43), (tam * 0.53, tam * 0.43),
    ]
    d.polygon(rayo, fill=(255, 194, 51, 255))
    img.save(ICONOS / f"icon-{tam}.png")
    print(f"OK: icon-{tam}.png")

print(f"OK: versión {hash_cuadros}, {len(resoluciones)} cuadros, actualizado {actualizado}")

#!/usr/bin/env python3
"""Genera versión de cuadros + íconos PWA. No editar los archivos de salida a mano."""
import hashlib
import json
from datetime import date
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # la versión se puede regenerar sin Pillow; los íconos se omiten
    Image = ImageDraw = None

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "datos" / "tarifas"
CLIENTE = RAIZ / "cliente"
ICONOS = CLIENTE / "icons"

# La caché debe cambiar también cuando cambia la interfaz, no solo los cuadros:
# si no, un cliente con el SW instalado no vuelve a descargar los assets nuevos.
UI = ("index.html", "app.js", "parser.js", "auditoria.js", "explicar.js",
      "payload.js", "history.js", "formulario.js", "resumen.js", "reclamo.js",
      "tarifas.js", "tablas.js", "sw.js", "manifest.webmanifest", "creditos.html",
      "img/hornocal-800.webp", "img/hornocal-1600.webp",
      "img/quebrada-tilcara-800.webp", "img/quebrada-tilcara-1600.webp",
      "img/salinas-800.webp", "img/salinas-1600.webp")

def _bytes_normalizados(ruta: Path) -> bytes:
    """CRLF -> LF solo en texto; los WebP son binarios y no se tocan."""
    datos = ruta.read_bytes()
    if ruta.suffix.lower() in {".json", ".js", ".html", ".webmanifest", ".css"}:
        return datos.replace(b"\r\n", b"\n")
    return datos


archivos = sorted(p for p in TABLAS.glob("*.json") if not p.name.startswith("_"))
interfaz = [CLIENTE / nombre for nombre in UI if (CLIENTE / nombre).exists()]
fuentes = archivos + interfaz
contenido = b"".join(_bytes_normalizados(p) for p in fuentes)
hash_version = hashlib.sha256(contenido).hexdigest()[:12]
actualizado = date.fromtimestamp(max(p.stat().st_mtime for p in fuentes)).isoformat()
resoluciones = [json.loads(p.read_text(encoding="utf-8"))["resolucion"] for p in archivos]

version = {
    "cache": f"boleta-justa-{hash_version}",
    "cuadros_hash": hash_version,
    "actualizado": actualizado,
    "resoluciones": resoluciones,
}
(CLIENTE / "version.json").write_text(
    json.dumps(version, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if Image:
    ICONOS.mkdir(exist_ok=True)
    for tam in (192, 512):
        img = Image.new("RGBA", (tam, tam), (247, 241, 230, 255))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([tam * 0.06, tam * 0.06, tam * 0.94, tam * 0.94],
                            radius=tam * 0.18, fill=(164, 70, 46, 255),
                            outline=(164, 70, 46, 255), width=max(2, tam // 64))
        rayo = [
            (tam * 0.56, tam * 0.16), (tam * 0.30, tam * 0.55),
            (tam * 0.48, tam * 0.55), (tam * 0.40, tam * 0.86),
            (tam * 0.72, tam * 0.43), (tam * 0.53, tam * 0.43),
        ]
        d.polygon(rayo, fill=(247, 241, 230, 255))
        img.save(ICONOS / f"icon-{tam}.png")
        print(f"OK: icon-{tam}.png")
else:
    print("OK: íconos omitidos (Pillow no instalado)")

print(f"OK: versión {hash_version}, {len(resoluciones)} cuadros, actualizado {actualizado}")

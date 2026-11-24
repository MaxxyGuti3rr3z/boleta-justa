"""Tests de vigilancia con respuestas simuladas (sin red)."""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import vigilar_boletin as v  # noqa: E402

FALLOS: list[str] = []


def check(condicion: bool, mensaje: str) -> None:
    if not condicion:
        FALLOS.append(mensaje)


ULTIMA = {"resolucion": "297-SUSEPU/2026", "numero": "297", "anio": "2026",
          "hasta": "2026-10-31", "desde": "2026-08-01"}
ROBOTS = "User-agent: *\nAllow: /\n"


def respuestas_base() -> dict[str, str]:
    salida: dict[str, str] = {}
    for _nombre, url in v.FUENTES:
        p = urlparse(url)
        salida[f"{p.scheme}://{p.netloc}/robots.txt"] = ROBOTS
        salida[url] = "Sin cuadro tarifario nuevo por acá."
    return salida


def fetch_de(respuestas: dict[str, str]):
    def fetch(url: str) -> str:
        if url not in respuestas:
            raise ConnectionError(f"fuente caída: {url}")
        return respuestas[url]
    return fetch


def pagina_boletin(con_novedad: bool) -> str:
    if con_novedad:
        return ('<a href="?p=999999">BOLETIN OFICIAL Nº 130 – 30/10/2026</a> '
                'RESOLUCION Nº 361-SUSEPU/2026.- CDE. EXPTE. CUADRO TARIFARIO, '
                'CON VIGENCIA A PARTIR DEL 1° DE NOVIEMBRE DE 2026')
    return 'RESOLUCION Nº 297-SUSEPU/2026.- CUADRO TARIFARIO CON VIGENCIA HASTA EL 31 DE OCTUBRE DE 2026'


def main() -> None:
    boletin, ejesa, susepu = (url for _n, url in v.FUENTES)

    # 1. sin novedades
    r = respuestas_base()
    r[boletin] = pagina_boletin(False)
    r[ejesa] = "Cuadro Tarifario Vigente. Aplicación Resolución N° 297-SUSEPU-2026"
    r[susepu] = "Cuadro tarifario vigente desde el 1 de Agosto del 2026"
    resultado = v.vigilar(fetch_de(r), {"notificados": []}, ULTIMA)
    check(resultado["novedades"] == [], "sin novedades: no debe avisar")
    check(all(f["estado"] == "ok" for f in resultado["fuentes"]),
          "sin novedades: las tres fuentes deben consultarse")

    # 2. resolución nueva con enlace
    r = respuestas_base()
    r[boletin] = pagina_boletin(True)
    r[ejesa] = "Cuadro Tarifario Vigente. Aplicación Resolución N° 297-SUSEPU-2026"
    r[susepu] = "Cuadro tarifario vigente desde el 1 de Agosto del 2026"
    resultado = v.vigilar(fetch_de(r), {"notificados": []}, ULTIMA)
    check(len(resultado["novedades"]) == 1, "resolución nueva: debe avisar una vez")
    if resultado["novedades"]:
        aviso = resultado["novedades"][0]
        check(aviso["clave"] == "361-SUSEPU/2026", "resolución nueva: clave incorrecta")
        check("?p=999999" in aviso["url"], "resolución nueva: debe traer el enlace del boletín")
        check(aviso["fuente"] == "boletin", "resolución nueva: fuente incorrecta")

    # 3. fuente caída: no rompe y sigue con las demás
    r = respuestas_base()
    del r[boletin]
    resultado = v.vigilar(fetch_de(r), {"notificados": []}, ULTIMA)
    estados = {f["fuente"]: f["estado"] for f in resultado["fuentes"]}
    check(estados.get("boletin") == "error", "fuente caída: debe registrar error")
    check(estados.get("ejesa") == "ok" and estados.get("susepu") == "ok",
          "fuente caída: las otras fuentes deben seguir")

    # 4. estado ya notificado: no repite aviso
    r = respuestas_base()
    r[boletin] = pagina_boletin(True)
    r[ejesa] = "Cuadro Tarifario Vigente. Aplicación Resolución N° 297-SUSEPU-2026"
    r[susepu] = "Cuadro tarifario vigente desde el 1 de Agosto del 2026"
    resultado = v.vigilar(fetch_de(r), {"notificados": ["361-SUSEPU/2026"]}, ULTIMA)
    check(resultado["novedades"] == [], "ya notificado: no debe repetir el aviso")

    if FALLOS:
        print(f"FALLOS ({len(FALLOS)}):")
        for fallo in FALLOS:
            print(" -", fallo)
        sys.exit(1)
    print("OK: vigilancia sin red (sin novedades, nueva, fuente caída, ya notificado)")


if __name__ == "__main__":
    main()

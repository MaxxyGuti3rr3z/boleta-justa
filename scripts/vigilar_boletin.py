#!/usr/bin/env python3
"""Vigila fuentes públicas por si aparece un cuadro tarifario nuevo.

Solo NOTIFICA: no carga resoluciones ni toca datos/tarifas/. Lee como máximo
una vez por fuente y ejecución, respeta robots.txt y usa un User-Agent
identificable. Ante un error de red, registra el problema y sigue.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.request
from datetime import date, datetime, timezone
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.robotparser import RobotFileParser

USER_AGENT = "boleta-justa-vigilancia"
RAIZ = Path(__file__).resolve().parent.parent
TABLAS = RAIZ / "datos" / "tarifas"
ESTADO = RAIZ / "datos" / "vigilancia_estado.json"

BOLETIN = "https://boletinoficial.jujuy.gob.ar/?s=SUSEPU+cuadro+tarifario"
EJESA = "https://www.ejesa.com.ar/info/pwa/institucional/costos-del-servicio"
SUSEPU = "https://susepu.jujuy.gob.ar/"
FUENTES = (("boletin", BOLETIN), ("ejesa", EJESA), ("susepu", SUSEPU))

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
RESOLUCION = re.compile(r"\b(\d{2,3})\s*[-/]\s*SUSEPU\s*[-/]?\s*(\d{4})\b", re.I)
VIGENCIA = re.compile(r"vigente\s+desde\s+el\s+(\d{1,2})\s+de\s+([a-záéíóú]+)\s+(?:del\s+)?(\d{4})", re.I)


class _Pagina(HTMLParser):
    """Extrae texto y anclas sin dependencias."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pedazos: list[str] = []
        self.enlaces: list[tuple[str, str, int]] = []
        self._href: str | None = None
        self._ancla: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href") or None
            self._ancla = []

    def handle_data(self, dato: str) -> None:
        self.pedazos.append(dato)
        if self._href is not None:
            self._ancla.append(dato)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.enlaces.append((self._href.strip(), " ".join(self._ancla).strip(),
                                 len(" ".join(self.pedazos))))
            self._href = None
            self._ancla = []

    @property
    def texto(self) -> str:
        return " ".join(" ".join(self.pedazos).split())


def _sin_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto)
                   if not unicodedata.combining(c)).lower()


def _resolucion_como_texto(numero: str, anio: str) -> str:
    return f"{int(numero):03d}-SUSEPU/{anio}"


def _es_mayor(numero: str, anio: str, ultima: dict) -> bool:
    return (int(anio), int(numero)) > (int(ultima["anio"]), int(ultima["numero"]))


def ultima_cargada() -> dict:
    """Devuelve la resolución/vigencia más reciente de datos/tarifas/."""
    cuadros = []
    for ruta in sorted(TABLAS.glob("*.json")):
        if ruta.name.startswith("_"):
            continue
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        cuadros.append(datos)
    if not cuadros:
        raise RuntimeError("no hay cuadros en datos/tarifas/")
    mejor = max(cuadros, key=lambda d: d["vigencia"]["hasta"])
    m = RESOLUCION.search(mejor["resolucion"])
    if not m:
        raise RuntimeError(f"resolución no reconocida: {mejor['resolucion']}")
    return {"resolucion": mejor["resolucion"], "numero": m.group(1), "anio": m.group(2),
            "hasta": mejor["vigencia"]["hasta"], "desde": mejor["vigencia"]["desde"]}


def _vigencia_de(texto: str) -> date | None:
    m = VIGENCIA.search(texto)
    if not m:
        return None
    mes = MESES.get(_sin_acentos(m.group(2)))
    if not mes:
        return None
    try:
        return date(int(m.group(3)), mes, int(m.group(1)))
    except ValueError:
        return None


def _enlace_para(pagina: _Pagina, clave: str, url: str, pos: int) -> str:
    """El texto de la resolución suele estar fuera del <a>: usa el ancla previa."""
    for href, texto, _idx in pagina.enlaces:
        if clave in _sin_acentos(texto) or clave in href:
            return href if href.startswith("http") else urljoin(url, href)
    # Los resultados del boletín enlazan con "?p="; los del menú usan "?page_id=".
    anteriores = [e for e in pagina.enlaces if e[2] <= pos and "?p=" in e[0]]
    if anteriores:
        href = anteriores[-1][0]
        return href if href.startswith("http") else urljoin(url, href)
    return url


def vigilar(fetch, estado: dict | None = None, ultima: dict | None = None,
            fuentes=FUENTES) -> dict:
    """Una pasada por las fuentes. `fetch(url) -> str` es inyectable para tests."""
    estado = estado or {"notificados": []}
    ultima = ultima or ultima_cargada()
    notificados = set(estado.get("notificados", []))
    fuentes_info: list[dict] = []
    novedades: list[dict] = []
    robots_por_host: dict[str, RobotFileParser | None] = {}
    visto: set[str] = set()

    for nombre, url in fuentes:
        partes = urlparse(url)
        host = partes.netloc
        try:
            if host not in robots_por_host:
                robots_url = f"{partes.scheme}://{partes.netloc}/robots.txt"
                try:
                    rp = RobotFileParser()
                    rp.parse(fetch(robots_url).splitlines())
                except Exception:
                    rp = None  # sin robots: se permite por convención
                robots_por_host[host] = rp
            rp = robots_por_host[host]
            if rp is not None and not rp.can_fetch(USER_AGENT, url):
                fuentes_info.append({"fuente": nombre, "url": url, "estado": "bloqueado_por_robots"})
                continue
            html = fetch(url)
            pagina = _Pagina()
            pagina.feed(html)
            texto = pagina.texto
            plano = _sin_acentos(texto)
            encontradas: list[dict] = []

            if nombre in ("boletin", "ejesa"):
                for m in RESOLUCION.finditer(texto):
                    numero, anio = m.group(1), m.group(2)
                    clave = _resolucion_como_texto(numero, anio)
                    if clave in visto:
                        continue
                    visto.add(clave)
                    # Solo el texto INMEDIATAMENTE posterior: el título de la
                    # búsqueda dice "cuadro tarifario" y daría falsos positivos.
                    ventana = plano[m.end(): m.end() + 300]
                    if "cuadro tarifario" not in ventana:
                        continue
                    fecha = _vigencia_de(texto[m.end():m.end() + 300])
                    if not _es_mayor(numero, anio, ultima) and not (fecha and fecha.isoformat() > ultima["hasta"]):
                        continue
                    encontradas.append({"clave": clave, "tipo": "resolucion", "valor": clave,
                                        "url": _enlace_para(pagina, clave, url, m.start())})
            elif nombre == "susepu":
                fecha = _vigencia_de(texto)
                if fecha and fecha.isoformat() > ultima["desde"]:
                    clave = f"vigencia-{fecha.isoformat()}"
                    if clave not in visto:
                        visto.add(clave)
                        encontradas.append({"clave": clave, "tipo": "vigencia",
                                            "valor": f"desde el {fecha.day} de {fecha.strftime('%B')} de {fecha.year}",
                                            "url": url})

            for item in encontradas:
                if item["clave"] in notificados:
                    continue
                item["fuente"] = nombre
                novedades.append(item)
            fuentes_info.append({"fuente": nombre, "url": url, "estado": "ok",
                                 "encontradas": len(encontradas)})
        except Exception as exc:
            fuentes_info.append({"fuente": nombre, "url": url, "estado": "error",
                                 "detalle": f"{type(exc).__name__}: {exc}"})

    return {"consultado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ultima_cargada": ultima["resolucion"], "fuentes": fuentes_info,
            "novedades": novedades}


def _fetch(url: str) -> str:
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(peticion, timeout=20) as respuesta:
        codificacion = respuesta.headers.get_content_charset() or "utf-8"
        return respuesta.read().decode(codificacion, errors="replace")


def main() -> int:
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"notificados": []}
    ultima = ultima_cargada()
    resultado = vigilar(_fetch, estado, ultima)
    if resultado["novedades"]:
        notificados = set(estado.get("notificados", []))
        notificados.update(n["clave"] for n in resultado["novedades"])
        estado["notificados"] = sorted(notificados)
        estado["actualizado"] = resultado["consultado"]
        estado["ultima_resolucion_conocida"] = ultima["resolucion"]
        ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

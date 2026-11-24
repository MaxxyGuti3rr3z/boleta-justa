#!/usr/bin/env python3
"""Valida el esquema de los cuadros tarifarios de datos/tarifas/.

Uso:
    python scripts/validar_cuadro.py                       # todos
    python scripts/validar_cuadro.py datos/tarifas/resNNN_YYYY-MM.json

Los archivos que empiezan con "_" (plantillas) se ignoran en la validación
global. No modifica ningún archivo.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TABLAS_DIR = RAIZ / "datos" / "tarifas"
NUMEROS = (int, float)
ALCANCE_ENERGIA = "t1_residencial.categorias[].energia_plena_kwh"
TIPOS_PARTIDA = {"cargo_fijo_y_uso_red", "energia_bloques", "porcentaje"}
RELACIONES = {"sustituye", "diferencial", "independiente"}
ZONAS = {"muy_calido", "calido", "resto"}
PERIODOS_ZONA = {"ene_feb_dic", "may_jun_jul_ago", "mar_abr_sep_oct_nov"}


def _numero(v) -> bool:
    return isinstance(v, NUMEROS) and not isinstance(v, bool)


def _texto(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _url(v) -> bool:
    return _texto(v) and v.startswith("https://")


def _son_numeros(v) -> bool:
    if isinstance(v, dict):
        return bool(v) and all(_son_numeros(x) for x in v.values())
    return _numero(v)


def _rango(datos: dict, prefijo: str, errores: list[str]) -> tuple[date | None, date | None]:
    fechas: dict[str, date] = {}
    for clave in ("desde", "hasta"):
        try:
            fechas[clave] = date.fromisoformat(str(datos.get(clave)))
        except (TypeError, ValueError):
            errores.append(f"{prefijo}.{clave} debe ser YYYY-MM-DD")
    if len(fechas) == 2 and fechas["desde"] > fechas["hasta"]:
        errores.append(f"{prefijo}: desde es posterior a hasta")
    return fechas.get("desde"), fechas.get("hasta")


def _validar_subperiodos(datos: dict, ids: set[str], errores: list[str]) -> None:
    subperiodos = datos.get("subperiodos", [])
    if not isinstance(subperiodos, list):
        errores.append("subperiodos debe ser una lista")
        return
    rangos: list[tuple[date, date]] = []
    for i, sub in enumerate(subperiodos):
        pref = f"subperiodos[{i}]"
        if not isinstance(sub, dict):
            errores.append(f"{pref} no es un objeto")
            continue
        for clave in ("resolucion", "publicacion", "fragmento"):
            if not _texto(sub.get(clave)):
                errores.append(f"{pref}: falta o es inválido {clave}")
        if not _url(sub.get("fuente")):
            errores.append(f"{pref}: fuente debe ser una URL https://")
        if sub.get("alcance") != ALCANCE_ENERGIA:
            errores.append(f"{pref}: alcance no permitido")
        rango = _rango(sub, pref, errores)
        if all(rango):
            rangos.append(rango)  # type: ignore[arg-type]
        valores = sub.get("valores")
        if not isinstance(valores, dict) or not valores:
            errores.append(f"{pref}: valores debe ser un objeto no vacío")
            continue
        for cid, valor in valores.items():
            if cid not in ids:
                errores.append(f"{pref}.valores: categoría desconocida {cid}")
            if not _numero(valor) or valor <= 0:
                errores.append(f"{pref}.valores.{cid}: debe ser > 0")
    for (a, b), (c, d) in combinations(rangos, 2):
        if a <= d and c <= b:
            errores.append("subperiodos con vigencias solapadas")


def _validar_partidas(datos: dict, errores: list[str]) -> None:
    bonificaciones = datos.get("bonificaciones")
    if bonificaciones is None:
        return
    if not isinstance(bonificaciones, dict):
        errores.append("bonificaciones debe ser un objeto")
        return
    for mes, bloque in bonificaciones.items():
        if mes == "nota":  # texto aclaratorio legacy, no es un mes
            if not isinstance(bloque, str):
                errores.append("bonificaciones.nota debe ser texto")
            continue
        if not re.fullmatch(r"\d{4}-\d{2}", str(mes)):
            errores.append(f"bonificaciones: mes inválido {mes}")
        if not isinstance(bloque, dict):
            errores.append(f"bonificaciones[{mes}] debe ser un objeto")
            continue
        partidas = bloque.get("partidas")
        if partidas is None:  # forma legacy: claves planas, se conserva
            continue
        if not isinstance(partidas, list):
            errores.append(f"bonificaciones[{mes}].partidas debe ser una lista")
            continue
        vistos: set[str] = set()
        for i, partida in enumerate(partidas):
            pref = f"bonificaciones[{mes}].partidas[{i}]"
            if not isinstance(partida, dict):
                errores.append(f"{pref} no es un objeto")
                continue
            pid = partida.get("id")
            if not _texto(pid):
                errores.append(f"{pref}: falta id")
            elif pid in vistos:
                errores.append(f"{pref}: id duplicado")
            else:
                vistos.add(str(pid))
            origen = partida.get("origen")
            if not isinstance(origen, dict):
                errores.append(f"{pref}: falta origen")
            else:
                for clave in ("resolucion", "fragmento"):
                    if not _texto(origen.get(clave)):
                        errores.append(f"{pref}.origen: falta o es inválido {clave}")
                if not _url(origen.get("fuente")):
                    errores.append(f"{pref}.origen.fuente debe ser una URL https://")
            _rango(partida, pref, errores)
            if partida.get("tipo") not in TIPOS_PARTIDA:
                errores.append(f"{pref}: tipo no permitido")
            valores = partida.get("valores")
            if not isinstance(valores, dict) or not valores or not all(
                    _son_numeros(v) for v in valores.values()):
                errores.append(f"{pref}: valores debe contener importes numéricos")


def _validar_referencia_sef(datos: dict, errores: list[str]) -> None:
    ref = datos.get("referencia_normativa_sef_2026")
    if ref is None:
        return
    if not isinstance(ref, dict):
        errores.append("referencia_normativa_sef_2026 debe ser un objeto")
        return
    for clave in ("resolucion", "publicacion", "fragmento", "fragmento_consumos_base"):
        if not _texto(ref.get(clave)):
            errores.append(f"referencia_normativa_sef_2026: falta o es inválido {clave}")
    if not _url(ref.get("fuente")):
        errores.append("referencia_normativa_sef_2026.fuente debe ser una URL https://")
    if ref.get("relacion") not in RELACIONES:
        errores.append("referencia_normativa_sef_2026.relacion no permitida")
    if not isinstance(ref.get("nota_discrepancia"), str):
        errores.append("referencia_normativa_sef_2026: falta nota_discrepancia")
    porcentajes = ref.get("porcentajes_bonificacion_total")
    if not isinstance(porcentajes, dict) or not porcentajes:
        errores.append("referencia_normativa_sef_2026.porcentajes_bonificacion_total inválido")
    else:
        for mes, valor in porcentajes.items():
            if not re.fullmatch(r"\d{4}-\d{2}", str(mes)):
                errores.append(f"referencia_normativa_sef_2026: mes inválido {mes}")
            if not _numero(valor) or not 0 <= valor <= 100:
                errores.append(f"referencia_normativa_sef_2026: porcentaje inválido en {mes}")
    zonas = ref.get("consumos_base_zona_kwh")
    if not isinstance(zonas, dict) or set(zonas) != ZONAS:
        errores.append("referencia_normativa_sef_2026.consumos_base_zona_kwh incompleto")
    else:
        for zona, periodos in zonas.items():
            if not isinstance(periodos, dict) or set(periodos) != PERIODOS_ZONA:
                errores.append(f"referencia_normativa_sef_2026: periodos inválidos en {zona}")
            elif not all(_numero(v) and v > 0 for v in periodos.values()):
                errores.append(f"referencia_normativa_sef_2026: consumos inválidos en {zona}")


def validar_archivo(ruta: Path) -> list[str]:
    """Devuelve una lista de errores; vacía si el cuadro es válido."""
    errores: list[str] = []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"no se pudo leer: {e}"]
    if not isinstance(datos, dict):
        return ["la raíz debe ser un objeto JSON"]

    for clave in ("resolucion", "publicacion", "fuente"):
        valor = datos.get(clave)
        if not isinstance(valor, str) or not valor.strip():
            errores.append(f"falta o es inválido: {clave}")
    # La nota puede estar vacía si el trimestre no tuvo pass through.
    if not isinstance(datos.get("nota_pass_through"), str):
        errores.append("falta o es inválido: nota_pass_through")

    fuente = datos.get("fuente")
    if isinstance(fuente, str) and fuente.strip() and not fuente.startswith("https://"):
        errores.append("fuente debe ser una URL https://")

    vigencia = datos.get("vigencia")
    if not isinstance(vigencia, dict):
        errores.append("falta vigencia {desde, hasta}")
    else:
        fechas = {}
        for clave in ("desde", "hasta"):
            valor = vigencia.get(clave)
            try:
                fechas[clave] = date.fromisoformat(str(valor))
            except (TypeError, ValueError):
                errores.append(f"vigencia.{clave} debe ser YYYY-MM-DD")
        if len(fechas) == 2 and fechas["desde"] > fechas["hasta"]:
            errores.append("vigencia.desde es posterior a vigencia.hasta")

    t1 = datos.get("t1_residencial")
    if not isinstance(t1, dict):
        errores.append("falta t1_residencial")
        return errores
    cats = t1.get("categorias")
    if not isinstance(cats, list) or not cats:
        errores.append("t1_residencial.categorias debe ser una lista no vacía")
        return errores

    ids: set[str] = set()
    topes: list[float] = []
    for i, cat in enumerate(cats):
        if not isinstance(cat, dict):
            errores.append(f"categoría {i} no es un objeto")
            continue
        cid = cat.get("id")
        if not isinstance(cid, str) or not cid.strip():
            errores.append(f"categoría {i}: falta id")
        elif cid in ids:
            errores.append(f"categoría {i}: id duplicado ({cid})")
        else:
            ids.add(cid)
        for clave in ("cargo_fijo", "uso_red_kwh", "energia_plena_kwh"):
            valor = cat.get(clave)
            if not _numero(valor) or valor <= 0:
                errores.append(f"categoría {i} ({cid}): {clave} debe ser > 0")
        tope = cat.get("hasta_kwh", "FALTA")
        if tope == "FALTA":
            errores.append(f"categoría {i} ({cid}): falta hasta_kwh")
        elif tope is None:
            if i != len(cats) - 1:
                errores.append(f"categoría {i} ({cid}): hasta_kwh null solo en la última")
        elif not _numero(tope):
            errores.append(f"categoría {i} ({cid}): hasta_kwh debe ser > 0 o null")
        elif tope <= 0:
            errores.append(f"categoría {i} ({cid}): hasta_kwh debe ser > 0 o null")
        else:
            topes.append(tope)

    if topes != sorted(topes):
        errores.append("los bloques (hasta_kwh) no están ordenados")
    if len(set(topes)) != len(topes):
        errores.append("hay topes de bloque repetidos")

    _validar_subperiodos(datos, ids, errores)
    _validar_partidas(datos, errores)
    _validar_referencia_sef(datos, errores)
    return errores


def validar_todos(carpeta: Path = TABLAS_DIR) -> list[str]:
    """Valida todos los cuadros y chequea que no se solapen las vigencias."""
    archivos = sorted(p for p in carpeta.glob("*.json") if not p.name.startswith("_"))
    errores: list[str] = []
    rangos: list[tuple[str, date, date]] = []
    for archivo in archivos:
        errores += [f"{archivo.name}: {e}" for e in validar_archivo(archivo)]
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        vig = datos.get("vigencia") if isinstance(datos, dict) else None
        if isinstance(vig, dict):
            try:
                rangos.append((archivo.name, date.fromisoformat(vig["desde"]),
                               date.fromisoformat(vig["hasta"])))
            except (KeyError, TypeError, ValueError):
                pass
    for (nombre_a, desde_a, hasta_a), (nombre_b, desde_b, hasta_b) in combinations(rangos, 2):
        if desde_a <= hasta_b and desde_b <= hasta_a:
            errores.append(f"vigencias solapadas: {nombre_a} y {nombre_b}")
    return errores


def main() -> int:
    if len(sys.argv) > 1:
        ruta = Path(sys.argv[1])
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        errores = validar_archivo(ruta)
        objetivo = ruta.name
    else:
        errores = validar_todos()
        cantidad = len([p for p in TABLAS_DIR.glob("*.json") if not p.name.startswith("_")])
        objetivo = f"{cantidad} cuadros en datos/tarifas/"
    if errores:
        print("ERRORES:")
        for error in errores:
            print(" -", error)
        return 1
    print(f"OK: esquema válido ({objetivo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

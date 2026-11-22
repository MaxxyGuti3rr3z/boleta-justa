"""Historial por usuario: SOLO el payload tarifario validado.

Nunca se guarda el PDF, el texto extraído, nombres, direcciones, DNI ni
identificadores de factura/suministro. La relación con la persona es el id
interno de usuario (un entero); el email tampoco se guarda en claro.
"""
from __future__ import annotations

import json
import sqlite3
import time

from payload_ia import validar


def guardar(conn: sqlite3.Connection, usuario_id: int, payload: dict,
            maximo: int = 50) -> int:
    validar(payload)  # rechaza cualquier campo o patrón personal
    ahora = time.time()
    aux = payload.get("auditoria") or {}
    cur = conn.execute(
        "INSERT INTO analisis (usuario_id, creado, mes, resolucion, payload) VALUES (?,?,?,?,?)",
        (usuario_id, ahora, payload.get("mes"), aux.get("resolucion"),
         json.dumps(payload, ensure_ascii=False)))
    conn.commit()
    # poda automática: solo los N más recientes por usuario
    viejos = conn.execute(
        "SELECT id FROM analisis WHERE usuario_id=? ORDER BY creado DESC", (usuario_id,)
    ).fetchall()[maximo:]
    for fila in viejos:
        conn.execute("DELETE FROM analisis WHERE id=?", (fila[0],))
    conn.commit()
    return int(cur.lastrowid or 0)


def listar(conn: sqlite3.Connection, usuario_id: int, limite: int = 50) -> list[dict]:
    filas = conn.execute(
        "SELECT id, creado, mes, resolucion FROM analisis WHERE usuario_id=? "
        "ORDER BY creado DESC LIMIT ?", (usuario_id, limite)).fetchall()
    return [{"id": f[0], "creado": f[1], "mes": f[2], "resolucion": f[3]} for f in filas]


def obtener(conn: sqlite3.Connection, usuario_id: int, analisis_id: int) -> dict | None:
    fila = conn.execute(
        "SELECT payload FROM analisis WHERE id=? AND usuario_id=?",
        (analisis_id, usuario_id)).fetchone()
    return json.loads(fila[0]) if fila else None


def borrar(conn: sqlite3.Connection, usuario_id: int, analisis_id: int) -> bool:
    cur = conn.execute("DELETE FROM analisis WHERE id=? AND usuario_id=?",
                       (analisis_id, usuario_id))
    conn.commit()
    return cur.rowcount > 0


def borrar_todos(conn: sqlite3.Connection, usuario_id: int) -> int:
    cur = conn.execute("DELETE FROM analisis WHERE usuario_id=?", (usuario_id,))
    conn.commit()
    return cur.rowcount


def limpiar_antiguos(conn: sqlite3.Connection, dias: int = 90) -> int:
    corte = time.time() - dias * 86400
    cur = conn.execute("DELETE FROM analisis WHERE creado<=?", (corte,))
    conn.commit()
    return cur.rowcount

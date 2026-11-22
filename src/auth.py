"""Autenticación mínima y segura para la API (opcional, AUTH_HABILITADO=1).

No guarda emails en claro: solo hash del email normalizado y hash de la clave
con scrypt + salt aleatorio. Las sesiones son tokens opacos; en la base se
guarda SOLO el hash del token, con vencimiento. Nada de esto se usa en el
cliente estático, que no tiene servidor ni cuentas.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from pathlib import Path

EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
N, R, P, DK = 2 ** 14, 8, 1, 32          # parámetros scrypt
DURACION_SESION = 24 * 3600             # segundos


def conectar(ruta: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(ruta))
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_hash TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        creado REAL NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sesiones (
        token_hash TEXT PRIMARY KEY,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        expira REAL NOT NULL)""")
    # Historial: SOLO payloads tarifarios validados (nunca PDFs ni datos de identidad)
    conn.execute("""CREATE TABLE IF NOT EXISTS analisis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        creado REAL NOT NULL,
        mes TEXT,
        resolucion TEXT,
        payload TEXT NOT NULL)""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_analisis_usuario ON analisis(usuario_id, creado DESC)")
    conn.commit()
    return conn


def _email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def _hash_clave(clave: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(clave.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=DK)
    return f"{salt.hex()}:{dk.hex()}"


def _verificar_clave(clave: str, guardado: str) -> bool:
    try:
        sal_hex, dk_hex = guardado.split(":", 1)
        dk = hashlib.scrypt(clave.encode("utf-8"), salt=bytes.fromhex(sal_hex),
                            n=N, r=R, p=P, dklen=DK)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, TypeError):
        return False


def registrar(email: str, clave: str, conn: sqlite3.Connection) -> int:
    if not EMAIL.match(email or ""):
        raise ValueError("email inválido")
    if len(clave or "") < 10:
        raise ValueError("la clave debe tener al menos 10 caracteres")
    eh = _email_hash(email)
    if conn.execute("SELECT 1 FROM usuarios WHERE email_hash=?", (eh,)).fetchone():
        raise ValueError("ese email ya está registrado")
    cur = conn.execute("INSERT INTO usuarios (email_hash, password_hash, creado) VALUES (?,?,?)",
                       (eh, _hash_clave(clave), time.time()))
    conn.commit()
    return int(cur.lastrowid or 0)


def verificar(email: str, clave: str, conn: sqlite3.Connection) -> int | None:
    fila = conn.execute("SELECT id, password_hash FROM usuarios WHERE email_hash=?",
                        (_email_hash(email or ""),)).fetchone()
    if not fila or not _verificar_clave(clave or "", fila[1]):
        return None
    return fila[0]


def crear_sesion(usuario_id: int, conn: sqlite3.Connection) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sesiones (token_hash, usuario_id, expira) VALUES (?,?,?)",
                 (hashlib.sha256(token.encode()).hexdigest(), usuario_id,
                  time.time() + DURACION_SESION))
    conn.commit()
    return token


def usuario_por_token(token: str | None, conn: sqlite3.Connection) -> int | None:
    if not token:
        return None
    fila = conn.execute("SELECT usuario_id FROM sesiones WHERE token_hash=? AND expira>?",
                        (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    return fila[0] if fila else None


def cerrar_sesion(token: str | None, conn: sqlite3.Connection) -> None:
    if token:
        conn.execute("DELETE FROM sesiones WHERE token_hash=?",
                     (hashlib.sha256(token.encode()).hexdigest(),))
        conn.commit()


def limpiar_vencidas(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM sesiones WHERE expira<=?", (time.time(),))
    conn.commit()
    return cur.rowcount

"""Tests de autenticación opcional (todo con datos sintéticos y DB temporal)."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import auth

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def main():
    with tempfile.TemporaryDirectory(prefix="auth-test-") as d:
        ruta = Path(d) / "auth.db"
        conn = auth.conectar(ruta)

        uid = auth.registrar("Vecina@Ejemplo.com", "clave-segura-123", conn)
        check(isinstance(uid, int) and uid > 0, "registro devuelve id")
        check(auth.verificar("vecina@ejemplo.com", "clave-segura-123", conn) == uid,
              "login con email normalizado")
        check(auth.verificar("vecina@ejemplo.com", "clave-incorrecta", conn) is None,
              "clave incorrecta rechazada")
        try:
            auth.registrar("vecina@ejemplo.com", "otra-clave-123", conn)
            check(False, "duplicado rechazado")
        except ValueError:
            pass
        try:
            auth.registrar("no-es-email", "clave-segura-123", conn)
            check(False, "email inválido rechazado")
        except ValueError:
            pass
        try:
            auth.registrar("otra@ejemplo.com", "corta", conn)
            check(False, "clave corta rechazada")
        except ValueError:
            pass

        crudo = ruta.read_bytes().decode("latin-1")
        check("vecina@ejemplo.com" not in crudo, "email no guardado en claro")
        check("clave-segura-123" not in crudo, "clave no guardada en claro")

        token = auth.crear_sesion(uid, conn)
        check(len(token) >= 30, "token opaco")
        check(auth.usuario_por_token(token, conn) == uid, "sesión válida")
        check(auth.usuario_por_token(None, conn) is None, "sin token")
        auth.cerrar_sesion(token, conn)
        check(auth.usuario_por_token(token, conn) is None, "logout invalida sesión")

        token2 = auth.crear_sesion(uid, conn)
        conn.execute("UPDATE sesiones SET expira=0")
        conn.commit()
        check(auth.usuario_por_token(token2, conn) is None, "sesión vencida rechazada")
        check(auth.limpiar_vencidas(conn) >= 1, "limpieza de vencidas")
        conn.close()

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: auth con scrypt, sin email/clave en claro, sesiones opacas y vencimiento")


if __name__ == "__main__":
    main()

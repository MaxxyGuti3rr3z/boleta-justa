"""Tests del historial: guarda SOLO payload validado, aislado por usuario."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import auth
import historial

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def payload(mes="2026-08"):
    return {
        "mes": mes, "categoria": "T1TS", "consumo_kwh": 189.4,
        "dias_facturados": 31.5,
        "energia": {"cargo_fijo": 4772.0, "precio_consumo": 141.7971,
                    "precio_red": 88.8382, "bonif_tarifa_social": -7417.13},
        "impuestos": {"iva_consumidor": 4155.82, "subtotal": 9843.9},
        "otros_cargos": {}, "agua": {"iva_punitorio": 430.54},
        "totales": {"a_pagar": 58500.0},
        "auditoria": {"estado": "auditada", "resolucion": "297-SUSEPU/2026",
                      "cargo_fijo_ok": True, "uso_red_ok": True,
                      "punitorios_signal": True, "punitorios_en_vigencia": True},
    }


def main():
    with tempfile.TemporaryDirectory(prefix="hist-test-") as d:
        ruta = Path(d) / "auth.db"
        conn = auth.conectar(ruta)
        u1 = auth.registrar("uno@ejemplo.com", "clave-segura-123", conn)
        u2 = auth.registrar("dos@ejemplo.com", "clave-segura-456", conn)

        aid = historial.guardar(conn, u1, payload())
        items = historial.listar(conn, u1)
        check(len(items) == 1 and items[0]["mes"] == "2026-08", "guardar y listar")
        check(items[0]["resolucion"] == "297-SUSEPU/2026", "resolucion indexada")
        obtenido = historial.obtener(conn, u1, aid)
        check(obtenido is not None and obtenido["categoria"] == "T1TS", "obtener payload")
        check(historial.listar(conn, u2) == [], "aislamiento por usuario")
        check(historial.obtener(conn, u2, aid) is None, "otro usuario no ve el análisis")
        check(not historial.borrar(conn, u2, aid), "otro usuario no borra")

        try:
            historial.guardar(conn, u1, {**payload(), "dni": 12345678})
            check(False, "rechaza payload con dato personal")
        except ValueError:
            pass

        for m in ("2026-09", "2026-10"):
            historial.guardar(conn, u1, payload(m))
        check(len(historial.listar(conn, u1)) == 3, "tres análisis")
        check(len(historial.listar(conn, u1)) == 3 and
              historial.guardar(conn, u1, payload("2026-11"), maximo=2) > 0,
              "guardar con poda")
        check(len(historial.listar(conn, u1)) == 2, "poda al máximo")

        restantes = [i["id"] for i in historial.listar(conn, u1)]
        check(historial.borrar(conn, u1, restantes[0]), "borrar propia")
        check(len(historial.listar(conn, u1)) == 1, "queda uno")
        check(historial.borrar_todos(conn, u1) >= 1, "borrar todo")
        check(historial.listar(conn, u1) == [], "historial vacío")

        historial.guardar(conn, u1, payload())
        check(historial.limpiar_antiguos(conn, dias=0) >= 1, "limpieza por retención")

        crudo = ruta.read_bytes().decode("latin-1")
        check("uno@ejemplo.com" not in crudo and "dos@ejemplo.com" not in crudo,
              "emails no en claro")
        check("clave-segura-123" not in crudo, "claves no en claro")
        conn.close()

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: historial aislado por id de usuario, payload validado, poda, borrado y retención")


if __name__ == "__main__":
    main()

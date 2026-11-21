"""Tests del limpiador de datos sensibles (fixtures sintéticas, sin boletas reales)."""
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "limpiar_sensibles.py"
FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def fixture():
    raiz = Path(tempfile.mkdtemp(prefix="limpieza-test-"))
    (raiz / "boletas_reales" / "_texto").mkdir(parents=True)
    (raiz / "boletas_reales" / "_parseado").mkdir(parents=True)
    (raiz / "boletas_reales" / "_texto" / "boleta_1.txt").write_text("texto sintetico")
    (raiz / "boletas_reales" / "_parseado" / "boleta_1.json").write_text("{}")
    (raiz / "boletas_reales" / "original.pdf").write_bytes(b"%PDF-1.4 sintetico")
    return raiz


def ejecutar(raiz, *args):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(raiz), *args],
                          capture_output=True, text=True, timeout=30)


def main():
    # dry-run no borra nada
    r1 = fixture()
    out = ejecutar(r1)
    check(out.returncode == 0, "dry-run exit 0")
    check("MODO DRY-RUN" in out.stdout, "dry-run avisado")
    check(len(list((r1 / "boletas_reales").rglob("*.*"))) == 3, "dry-run conserva archivos")

    # --apply borra derivados y conserva originales
    r2 = fixture()
    out = ejecutar(r2, "--apply")
    check(out.returncode == 0, "apply exit 0")
    check((r2 / "boletas_reales" / "original.pdf").exists(), "original conservado")
    check(not (r2 / "boletas_reales" / "_texto").exists(), "_texto borrado")
    check(not (r2 / "boletas_reales" / "_parseado").exists(), "_parseado borrado")

    # --include-originals borra todo
    r3 = fixture()
    out = ejecutar(r3, "--apply", "--include-originals")
    check(out.returncode == 0, "apply total exit 0")
    check(not (r3 / "boletas_reales" / "original.pdf").exists(), "original borrado")

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: limpieza dry-run/apply/total con datos sintéticos")


if __name__ == "__main__":
    main()

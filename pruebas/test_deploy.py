"""Tests del modo despliegue público (config y límite de uso, datos sintéticos)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import config

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def main():
    # texto de consentimiento: cambia según el modo
    check("no se sube a ningún servidor" in config.CONSENTIMIENTO_LOCAL,
          "modo local promete procesamiento local")
    check("se envía a este servidor" in config.CONSENTIMIENTO_PUBLICO,
          "modo público avisa que se envía el PDF")
    check("descargá el proyecto" in config.CONSENTIMIENTO_PUBLICO,
          "modo público ofrece alternativa local")
    check(not config.PUBLICO, "por defecto modo local (MODO_PUBLICO no seteado)")

    # límite de solicitudes por IP
    l = config.Limitador(maximo=3, ventana=60)
    check(l.permite("1.2.3.4", ahora=0), "paso 1")
    check(l.permite("1.2.3.4", ahora=1), "paso 2")
    check(l.permite("1.2.3.4", ahora=2), "paso 3")
    check(not l.permite("1.2.3.4", ahora=3), "paso 4 bloqueado")
    check(l.permite("5.6.7.8", ahora=3), "otra IP no se ve afectada")
    check(l.permite("1.2.3.4", ahora=61), "se libera al vencer la ventana")

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: modo público/local, consentimiento honesto, rate limit por IP")


if __name__ == "__main__":
    main()

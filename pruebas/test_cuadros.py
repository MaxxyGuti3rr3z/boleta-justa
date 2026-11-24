"""Tests del validador de cuadros (JSON sintéticos, sin boletas reales)."""
import json
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "src"))
import validar_cuadro as vc
import auditoria

FALLOS = []


def check(cond, mensaje):
    if not cond:
        FALLOS.append(mensaje)


def cuadro(resolucion="999-SUSEPU/2099", desde="2099-01-01", hasta="2099-03-31"):
    return {
        "resolucion": resolucion,
        "publicacion": "Boletín sintético",
        "fuente": "https://ejemplo.invalid/resolucion",
        "vigencia": {"desde": desde, "hasta": hasta},
        "nota_pass_through": "",
        "t1_residencial": {"categorias": [
            {"id": "R1", "hasta_kwh": 150, "cargo_fijo": 1.0,
             "uso_red_kwh": 1.0, "energia_plena_kwh": 1.0},
            {"id": "R2", "hasta_kwh": None, "cargo_fijo": 2.0,
             "uso_red_kwh": 2.0, "energia_plena_kwh": 2.0},
        ]},
    }


def escribir(carpeta: Path, nombre: str, datos: dict) -> Path:
    p = carpeta / nombre
    p.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return p


def main():
    check(vc.validar_todos() == [], "los 6 cuadros reales son válidos")
    tablas = auditoria.cargar_tablas()
    check(len(tablas) == 6, "la plantilla no se carga como cuadro")
    check(all(t.get("resolucion") for t in tablas), "ningún cuadro vacío")

    with tempfile.TemporaryDirectory(prefix="cuadros-test-") as d:
        carpeta = Path(d)
        check(vc.validar_archivo(escribir(carpeta, "valido.json", cuadro())) == [],
              "cuadro sintético válido")

        mal = cuadro()
        del mal["resolucion"]
        check(any("resolucion" in e for e in vc.validar_archivo(
            escribir(carpeta, "sin_res.json", mal))), "falta resolución")

        mal = cuadro()
        mal["vigencia"] = {"desde": "2099-05-01", "hasta": "2099-01-01"}
        check(any("posterior" in e for e in vc.validar_archivo(
            escribir(carpeta, "fechas.json", mal))), "fechas invertidas")

        mal = cuadro()
        mal["t1_residencial"]["categorias"][1]["hasta_kwh"] = 100
        check(any("ordenados" in e for e in vc.validar_archivo(
            escribir(carpeta, "desorden.json", mal))), "bloques desordenados")

        mal = cuadro()
        mal["t1_residencial"]["categorias"][1]["id"] = "R1"
        check(any("duplicado" in e for e in vc.validar_archivo(
            escribir(carpeta, "dup.json", mal))), "id duplicado")

        mal = cuadro()
        mal["t1_residencial"]["categorias"][0]["cargo_fijo"] = -1
        check(any("cargo_fijo" in e for e in vc.validar_archivo(
            escribir(carpeta, "negativo.json", mal))), "precio no positivo")

        # campos opcionales nuevos: subperíodos, partidas y referencia SEF
        def sub(fragmento="texto", desde="2099-02-01", hasta="2099-02-28"):
            return {"id": "sp", "desde": desde, "hasta": hasta,
                    "resolucion": "999/2099", "publicacion": "BO sintético",
                    "fuente": "https://ejemplo.invalid/resolucion",
                    "fragmento": fragmento,
                    "alcance": "t1_residencial.categorias[].energia_plena_kwh",
                    "valores": {"R1": 2.0}}

        bueno = cuadro()
        bueno["subperiodos"] = [sub()]
        check(vc.validar_archivo(escribir(carpeta, "sp_ok.json", bueno)) == [],
              "subperiodo válido")

        mal = cuadro()
        mal["subperiodos"] = [sub(fragmento="")]
        check(any("fragmento" in e for e in vc.validar_archivo(
            escribir(carpeta, "sp_sin_fragmento.json", mal))), "subperiodo sin fragmento")

        mal = cuadro()
        mal["subperiodos"] = [sub(), sub()]
        check(any("solapadas" in e for e in vc.validar_archivo(
            escribir(carpeta, "sp_solape.json", mal))), "subperiodos solapados")

        mal = cuadro()
        mal["subperiodos"] = [{"id": "sp", "desde": "2099-02-01", "hasta": "2099-02-28",
                               "resolucion": "999", "publicacion": "BO", "fuente": "https://ejemplo.invalid/r",
                               "fragmento": "texto", "alcance": "t1_residencial.categorias[].energia_plena_kwh",
                               "valores": {"RX": 2.0}}]
        check(any("desconocida" in e for e in vc.validar_archivo(
            escribir(carpeta, "sp_categoria.json", mal))), "subperiodo con categoría inexistente")

        def partida(con_origen=True):
            p = {"id": "p", "desde": "2099-02-01", "hasta": "2099-02-28",
                 "tipo": "energia_bloques", "valores": {"R1": -1.0}}
            if con_origen:
                p["origen"] = {"resolucion": "999/2099", "fuente": "https://ejemplo.invalid/r",
                               "fragmento": "texto"}
            return p

        bueno = cuadro()
        bueno["bonificaciones"] = {"2099-02": {"nota": "texto"},
                                   "2099-03": {"partidas": [partida()]}}
        check(vc.validar_archivo(escribir(carpeta, "partida_ok.json", bueno)) == [],
              "partida con origen y nota legacy")

        mal = cuadro()
        mal["bonificaciones"] = {"2099-02": {"partidas": [partida(False)]}}
        check(any("origen" in e for e in vc.validar_archivo(
            escribir(carpeta, "partida_sin_origen.json", mal))), "partida sin origen")

        def referencia(porcentaje=70.45):
            return {"resolucion": "999/2099", "publicacion": "BO",
                    "fuente": "https://ejemplo.invalid/105",
                    "fragmento": "texto", "fragmento_consumos_base": "texto",
                    "relacion": "diferencial", "nota_discrepancia": "",
                    "porcentajes_bonificacion_total": {"2099-02": porcentaje},
                    "consumos_base_zona_kwh": {
                        z: {"ene_feb_dic": 300, "may_jun_jul_ago": 300,
                            "mar_abr_sep_oct_nov": 150}
                        for z in ("muy_calido", "calido", "resto")}}

        bueno = cuadro()
        bueno["referencia_normativa_sef_2026"] = referencia()
        check(vc.validar_archivo(escribir(carpeta, "ref_ok.json", bueno)) == [],
              "referencia SEF válida")

        mal = cuadro()
        mal["referencia_normativa_sef_2026"] = referencia(120)
        check(any("porcentaje" in e for e in vc.validar_archivo(
            escribir(carpeta, "ref_porcentaje.json", mal))), "porcentaje fuera de rango")

        # solapamiento entre dos cuadros en la misma carpeta
        overlap = carpeta / "overlap"
        overlap.mkdir()
        escribir(overlap, "a.json", cuadro("999-SUSEPU/2099", "2099-01-01", "2099-03-31"))
        escribir(overlap, "b.json", cuadro("998-SUSEPU/2099", "2099-03-01", "2099-05-31"))
        check(any("solapadas" in e for e in vc.validar_todos(overlap)), "vigencias solapadas")

    if FALLOS:
        print("FALLOS (%d):" % len(FALLOS))
        for f in FALLOS:
            print(" -", f)
        sys.exit(1)
    print("OK: validador de cuadros (esquema, fechas, bloques, solapes y plantilla ignorada)")


if __name__ == "__main__":
    main()

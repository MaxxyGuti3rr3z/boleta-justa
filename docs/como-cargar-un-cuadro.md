# Cómo cargar un cuadro tarifario nuevo

Esta guía es para agregar un trimestre nuevo a `datos/tarifas/`. La fuente de
verdad son los archivos JSON de esa carpeta; `cliente/tablas.js` se genera desde
ellos y **nunca se edita a mano**.

## 1. Buscar la resolución (sin inventar datos)

1. Entrar al Boletín Oficial de Jujuy: https://boletinoficial.jujuy.gob.ar/
2. Buscar por `SUSEPU` + `cuadro tarifario` + el período buscado. También puede
   aparecer como `Res. SUSEPU/2026` o referida a EJESA.
3. Verificar que sea el **anexo del cuadro tarifario**, no una nota de
   actualización de precios dentro del trimestre (eso va en `nota_pass_through`).
4. Si no aparece, **no inventar la resolución ni los valores**: dejar el
   trimestre sin cargar. La app ya muestra el aviso "cuadro no disponible" y
   sugiere pedirle el desglose a EJESA.

Los cuadros ya cargados tienen URLs reales que sirven de ejemplo:

- `res168_2025-05.json` → https://boletinoficial.jujuy.gob.ar/?p=310162
- `res296_2025-08.json` → https://boletinoficial.jujuy.gob.ar/?p=316892
- `res420_2025-11.json` → https://boletinoficial.jujuy.gob.ar/?p=322524
- `res81_2026-02.json` → https://boletinoficial.jujuy.gob.ar/?p=328410
- `res227_2026-05.json` → https://boletinoficial.jujuy.gob.ar/?p=433937
- `res297_2026-08.json` → https://boletinoficial.jujuy.gob.ar/?p=435659

## 2. Copiar los campos al JSON

Usar `datos/tarifas/_plantilla.json` como base. Nombre de archivo:
`res<numero>_<YYYY-MM>.json`, donde la fecha es el inicio de vigencia.

Campos obligatorios:

| Campo | Qué copiar |
|---|---|
| `resolucion` | Número y año exactos de la resolución, p. ej. `297-SUSEPU/2026` |
| `publicacion` | Referencia del Boletín Oficial (número y fecha) |
| `fuente` | URL de la publicación oficial |
| `vigencia.desde` / `vigencia.hasta` | Fechas ISO `YYYY-MM-DD` del trimestre |
| `nota_pass_through` | Explicación de las actualizaciones de energía dentro del trimestre, si las hay |
| `t1_residencial.categorias` | Lista de bloques con `id`, `hasta_kwh`, `cargo_fijo`, `uso_red_kwh`, `energia_plena_kwh` |

Reglas para los bloques:

- `id`: `R1`, `R2`, `R2-bis`, `R3`, etc., tal como figura en el cuadro.
- `hasta_kwh`: tope acumulativo (150, 250, 350...). Solo la última categoría
  puede tener `null` (sin límite).
- `cargo_fijo` y `uso_red_kwh` (VAD): se mantienen durante todo el trimestre.
- `energia_plena_kwh`: precio base; si cambia dentro del trimestre, NO se crea
  otro cuadro: se documenta en `nota_pass_through`.
- Los bloques van ordenados por `hasta_kwh` y sin topes repetidos.

No copiar importes "de ejemplo" ni completar casillas con valores parecidos.
Si el texto de la resolución no dice un valor, ese valor no se carga.

## 3. Validar el esquema

```bash
cd boleta-justa
py -3.13 scripts/validar_cuadro.py                       # valida todos los cuadros
py -3.13 scripts/validar_cuadro.py datos/tarifas/resNNN_YYYY-MM.json  # uno solo
```

El script comprueba campos obligatorios, fechas coherentes, bloques ordenados,
sin solapamiento de vigencias entre cuadros e ignora la plantilla (`_`).
También valida los campos opcionales `subperiodos`, `bonificaciones.partidas` y
`referencia_normativa_sef_2026`: exigen resolución, fragmento y fuente HTTPS,
categorías conocidas y vigencias que no se solapen.

## 4. Regenerar el cliente y probar

```bash
py -3.13 scripts/generar_tablas_js.py
py -3.13 scripts/generar_version_pwa.py      # actualiza version.json y la caché del SW
for t in tarifas decreto parser auditoria cuadros explicar deploy limpieza preguntas auth historial paridad; do
  ./venv/Scripts/python.exe pruebas/test_$t.py
done
node --test pruebas-js/*.test.mjs            # 12 archivos / 84 tests
```

Si el cuadro nuevo coincide con una boleta local, la auditoría debe pasar de
`cuadro_no_disponible` a `auditada` con confianza alta. Verificar en el panel
local (`./venv/Scripts/python.exe src/api.py`) y en el cliente estático
(`py -3.13 -m http.server 8100 --directory cliente`).

## 5. Publicar

La web estática se actualiza subiendo la carpeta `cliente/` al repo
`boleta-justa-web`. **No hacer commit ni push sin pedirlo explícitamente.**

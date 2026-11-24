# Documentación general de Boleta Justa

Fecha de esta versión: 24/11/2026.

## 1. Resumen ejecutivo

Boleta Justa es un proyecto cívico para que cualquier persona en Jujuy pueda
entender y revisar su factura de luz de EJESA sin depender de la empresa ni de
un abogado. Toma un PDF de boleta, extrae solo los datos de facturación, los
compara con los cuadros tarifarios oficiales del trimestre correspondiente y
devuelve una explicación en lenguaje llano.

La versión pública es un sitio estático que hace todo en el navegador: el PDF
nunca se sube a ningún servidor. La API local existe para desarrollo y para
funciones opcionales (login, historial en servidor, IA).

- Sitio público: https://maxxyguti3rr3z.github.io/boleta-justa-web/
- Código: https://github.com/MaxxyGuti3rr3z/boleta-justa
- Web estática: https://github.com/MaxxyGuti3rr3z/boleta-justa-web
- Marco normativo con fuentes: `docs/marco-normativo.md`
- Plan de privacidad: `docs/plan-cero-riesgo.md`
- Licencia: MIT (con nota de datos oficiales)

## 2. Origen y problema

El proyecto surgió de una exploración más amplia sobre necesidades concretas en
Jujuy. El relevamiento encontró, entre otros problemas: facturas elevadas en
hogares vulnerables, impuestos que representan una parte importante del total,
cortes que no respetarían los plazos del decreto de emergencia, falta de
oficinas para reclamar en el interior y movimientos vecinales con miles de
firmas. Todo eso está documentado con fuentes en `docs/marco-normativo.md` y en
fichas de exploración que viven fuera de este repositorio.

La hipótesis de trabajo fue: si la persona entiende su boleta y tiene el cuadro
oficial al lado, puede detectar errores y reclamos con argumentos, sin depender
de un trámite presencial.

Proyecto hermano: `cuando-llega-jujuy`
(https://github.com/MaxxyGuti3rr3z/cuando-llega-jujuy), de transporte público.

## 3. Estado actual

- Sitio estático publicado y verificado en navegador con una boleta ficticia
  (HTTP 200, resultado correcto, historial local funcionando).
- API local funcionando con 19 endpoints.
- 6 cuadros tarifarios históricos cargados desde el Boletín Oficial, con
  subperíodos de energía y bonificaciones documentadas (Res. 476/2025 y
  105/2026) y la rectificación 104/2026.
- Cliente con pdf.js local, CSP estricta, PWA instalable (manifest, service
  worker y versión de caché) e identidad visual con fotos de Jujuy y créditos.
- 12 suites de tests Python y 12 archivos / 84 tests Node, todos verdes.
- `python scripts/validar_cuadro.py` y `pruebas-js/sin-cdn.test.mjs` (URLs
  externas) también verdes.
- Última verificación de CI en el commit publicado: `success`.
- Los cambios de esta última iteración están en el árbol de trabajo, listos
  para commitear y publicar (sin commit todavía).
- Sin servidores corriendo de forma permanente.

## 4. Arquitectura

Hay dos superficies que comparten la misma lógica de negocio:

```
   SITIO PÚBLICO (GitHub Pages)          API LOCAL / DESARROLLO
   ┌──────────────────────────┐          ┌──────────────────────────┐
   │ cliente/index.html       │          │ web/index.html           │
   │ pdf.js lee el PDF        │          │ FastAPI (src/api.py)     │
   │ parser.js                │          │ parser_boletas.py        │
   │ auditoria.js             │          │ auditoria.py             │
   │ explicar.js              │          │ explicar.py              │
    │ payload.js / history.js  │          │ payload_ia / preguntas   │
    │ formulario.js (manual)   │          │ auth / historial         │
    │ resumen.js / reclamo.js  │          │ SQLite opcional          │
    │ sw.js + manifest + img/  │          │                          │
    │ localStorage / SIN BACKEND│         │                          │
    └──────────────────────────┘          └──────────────────────────┘
        PDF nunca sale                       PDF se sube a localhost
        del dispositivo                       y se borra al terminar
```

Regla: la lógica de negocio vive en `src/` (Python) y se replica en `cliente/`
(JS). Los cuadros tarifarios son la fuente de verdad en `datos/tarifas/*.json`;
`scripts/generar_tablas_js.py` genera `cliente/tablas.js` para el sitio estático.
Los cuadros pueden definir `subperiodos` (precio de energía vigente dentro del
trimestre) y `bonificaciones` con partidas documentadas; el calculador aplica
el subperiodo sin tocar el VAD. La PWA se genera con
`scripts/generar_version_pwa.py`: el hash de caché cubre datos, UI, fotos y
créditos, y el service worker precachea solo assets estáticos (nunca el PDF).

## 5. Mapa de archivos

### Núcleo Python (`src/`)

| Archivo | Responsabilidad |
|---|---|
| `tarifas.py` | Calculadora T1: cargo fijo, red, energía, bonificaciones TS/SEF/RE por bloques |
| `decreto.py` | Verificador del Decreto Acuerdo 5658-JG/2026: plazos de corte (20 días), retiro de medidor (60) y punitorios |
| `parser_boletas.py` | Lee PDFs con pypdf y extrae SOLO campos tarifarios a JSON |
| `inspeccionar_boletas.py` | Inspección segura: consola enmascarada, texto crudo solo en local |
| `auditoria.py` | Selecciona el cuadro por VAD y compara la boleta |
| `explicar.py` | Convierte el resultado técnico en frases para no técnicos |
| `preguntas.py` | Respuestas determinísticas sobre la boleta, sin modelo externo |
| `payload_ia.py` | Construye y valida el JSON mínimo que podría recibir una IA |
| `ia_client.py` | Cliente opcional de chat completions (solo con credenciales) |
| `config.py` | Flags de modo público, auth, límites y textos de consentimiento |
| `auth.py` | Login opcional con scrypt, email hasheado y sesiones opacas |
| `historial.py` | Historial por id de usuario: solo payload validado |
| `api.py` | FastAPI: sirve la UI y expone todos los endpoints |

### Cliente estático (`cliente/`)

| Archivo | Responsabilidad |
|---|---|
| `index.html` | Landing con identidad Jujuy, carga, resultado, nav de anclas y créditos |
| `app.js` | Orquesta lectura del PDF, análisis y render; conecta el historial local |
| `parser.js` | Port del parser a JavaScript |
| `auditoria.js` | Port de la auditoría (VAD + bloques) |
| `explicar.js` | Port de las explicaciones y avisos "a verificar" por resolución aplicada |
| `payload.js` | Lista blanca y validación del payload exportable |
| `history.js` | Historial en `localStorage`, copia de seguridad y recuperación |
| `formulario.js` | Carga manual sin OCR: produce el mismo objeto interno del parser |
| `resumen.js` / `reclamo.js` | Resumen para compartir y solicitud de desglose (sin veredictos) |
| `tablas.js` | Generado desde los 6 JSON oficiales; no editar a mano |
| `tarifas.js` | Port de `src/tarifas.py` con subperíodos y bonificaciones |
| `sw.js` / `manifest.webmanifest` / `version.json` | PWA: precaché de assets, instalación y versión de caché |
| `img/` / `creditos.html` | 3 fotos WebP (cabecera + 2) y créditos con licencias verificadas |
| `vendor/pdfjs/` | pdf.js 6.5.438 + worker + LICENSE + README con hashes (sin CDN) |

### Datos, docs y tooling

- `datos/tarifas/`: 6 cuadros oficiales con resolución, vigencia y fuente.
- `docs/marco-normativo.md`: decretos, resoluciones y recortes con citas.
- `docs/plan-cero-riesgo.md`: decisión de privacidad y estado de la migración.
- `docs/captura-*.png`: capturas de la UI (sin datos personales).
- `scripts/generar_tablas_js.py`: regenera `tablas.js`.
- `scripts/limpiar_sensibles.py`: limpieza controlada de datos sensibles.
- `pruebas/` (12 suites) y `pruebas-js/` (12 archivos, 84 tests).
- `.github/workflows/tests.yml`: CI con Python 3.13 y Node 22.

## 6. Flujo de datos y privacidad

1. La persona elige un PDF.
2. En el sitio público, pdf.js extrae el texto **en el navegador**. En la API
   local se usa un archivo temporal que se borra al salir del `with`.
3. El parser guarda en memoria solo campos de facturación. Nunca extrae
   nombres, direcciones, DNI/CUIT, números de suministro, usuario ni factura.
4. La auditoría compara contra cuadros públicos. El resultado son booleanos,
   porcentajes y la resolución aplicable: nunca importes personales.
5. La explicación se arma con frases. El payload opcional para IA pasa por una
   lista blanca (`payload_ia.py` / `payload.js`) y se valida antes de viajar.
6. El historial local guarda solo ese payload validado (máximo 20 en el
   navegador). El historial en servidor, si se activa, usa el id interno del
   usuario (máximo 50, 90 días de retención).

Lo que NUNCA se guarda ni se envía: el PDF, el texto crudo, nombres,
direcciones, DNI y números de cuenta. `boletas_reales/` y sus derivados están
gitignoreados. El script de limpieza permite borrar derivados y, con un flag
explícito, los originales; por defecto es solo dry-run.

## 7. Reglas de negocio aprendidas

- **Elección del cuadro**: no se usa la fecha de emisión, porque varias boletas
  facturan períodos anteriores. Se elige por coincidencia de los componentes
  VAD (cargo fijo + uso de red), estables dentro del trimestre, y se informa la
  confianza (alta/media/baja).
- **Uso de red por bloques**: el precio unitario impreso no es el de una
  categoría, sino el promedio ponderado de bloques acumulativos (R1 0-150 kWh,
  R2 150-250, R2-bis 250-350, R3 350-500...). Compararlo con una sola fila del
  cuadro daba falsos DIFIERE. Verificado con aritmética exacta en 5/5 boletas.
- **Tarifa social**: aparece como renglón negativo propio, no reduciendo el
  precio unitario de cada kWh.
- **Pass through**: el precio de la energía puede subir 2-4% dentro del
  trimestre por actualizaciones nacionales. Eso no es un error de facturación.
- **Punitorios**: de 4 boletas con señal, solo 1 cae dentro de la vigencia del
  Decreto 5658 (desde el 20/07/2026, Art. 3.C). Las anteriores no se reclaman
  por esa norma. Siempre son señales a verificar, nunca veredictos legales.
- **Sin veredictos**: la herramienta orienta y cita fuentes; no afirma
  irregularidades ni reemplaza un reclamo formal.
- **Paridad y redondeo**: `pruebas/casos_paridad/*.json` se ejecuta en Python y
  en JS con los mismos casos. Los importes del cuadro son decimales; al
  redondear a 2 lugares se usa tolerancia al error binario
  (350 kWh × 159,1277 = 55.694,695 → $55.694,70) y cero positivo en ambos
  lados. El marco normativo no fija el criterio de redondeo: se adoptó el
  redondeo decimal habitual para no perder un centavo por representación
  binaria.

## 8. Cuadros tarifarios y fuentes

| Resolución | Vigencia | Fuente |
|---|---|---|
| 168-SUSEPU/2025 | 2025-05-01 → 2025-07-31 | https://boletinoficial.jujuy.gob.ar/?p=310162 |
| 296-SUSEPU/2025 | 2025-08-01 → 2025-10-31 | https://boletinoficial.jujuy.gob.ar/?p=316892 |
| 420-SUSEPU/2025 | 2025-11-01 → 2026-01-31 | https://boletinoficial.jujuy.gob.ar/?p=322524 |
| 81-SUSEPU/2026 | 2026-02-01 → 2026-04-30 | https://boletinoficial.jujuy.gob.ar/?p=328410 |
| 227-SUSEPU/2026 | 2026-05-01 → 2026-07-31 | https://boletinoficial.jujuy.gob.ar/?p=433937 |
| 297-SUSEPU/2026 | 2026-08-01 → 2026-10-31 | https://boletinoficial.jujuy.gob.ar/?p=435659 |

Las resoluciones dentro del trimestre que cambian el precio de energía (pass
through) están aclaradas en la nota `nota_pass_through` de cada JSON. La
resolución del trimestre nov-2026/ene-2027 no estaba publicada/indexada en la
última búsqueda: no se afirma que no exista, simplemente no está cargada.

## 9. Funcionalidades

### Sitio público
- Carga de PDF por selector o arrastrar y soltar.
- Auditoría con resolución elegida, confianza, comparación por renglón y notas.
- Explicación en lenguaje llano y glosario desplegable.
- Historial local: guardar, ver, borrar con confirmación, y copia de seguridad
  (guardar/recuperar) para pasar los análisis a otro dispositivo.
- Carga manual (sin OCR) para boletas en papel o PDF escaneado: si el PDF no
  tiene texto útil, se ofrece un formulario guiado que produce el mismo objeto
  interno que `parser.js` y reutiliza la auditoría y la explicación.

### API local / panel
- Landing + panel con pestañas Simulador, Verificador y Auditoría.
- Simulador: consumo + mes + tarifa social/SEF/electrodependiente → desglose.
- Verificador del decreto: corte, retiro de medidor y punitorios con citas.
- Auditoría de las 5 boletas de ejemplo y carga de un PDF propio.
- Preguntas sobre la boleta, con respuesta determinística por defecto.
- IA opcional con payload mínimo validado (nunca el PDF).
- Login opcional e historial en servidor, ambos desactivados por defecto.

## 10. Endpoints de la API

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/config` | Modo público, límites y texto de consentimiento |
| GET | `/api/health` | Health check |
| GET | `/api/cuadro` | Cuadro vigente |
| POST | `/api/calcular` | Simulación tarifaria |
| POST | `/api/verificar/corte` | Plazo de corte |
| POST | `/api/verificar/retiro` | Retiro de medidor |
| POST | `/api/verificar/punitorios` | Intereses punitorios |
| POST | `/api/auditar` | Sube un PDF y devuelve auditoría + explicación + payload |
| POST | `/api/preguntar` | Preguntas con payload mínimo (IA opcional) |
| GET | `/api/auditoria` | Ejemplos del dueño (desactivado en modo público) |
| POST | `/api/auth/registro` | Registro (si auth habilitada) |
| POST | `/api/auth/login` | Login con cookie segura |
| POST | `/api/auth/logout` | Cierre de sesión |
| GET | `/api/auth/yo` | Estado de sesión |
| POST | `/api/analisis` | Guardar payload del usuario |
| GET | `/api/analisis` | Listar metadatos del historial |
| GET | `/api/analisis/{id}` | Ver payload de un análisis propio |
| DELETE | `/api/analisis/{id}` | Borrar un análisis |
| DELETE | `/api/analisis` | Borrar todo el historial propio |

## 11. Instalación y uso

Requisitos: Python 3.13 con `venv`, Node 22 para los tests JS.

```bash
cd boleta-justa
py -3.13 -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt

# API local
./venv/Scripts/python.exe src/api.py        # http://127.0.0.1:8101

# Sitio estático local
py -3.13 scripts/generar_tablas_js.py
py -3.13 -m http.server 8100 --directory cliente

# Tests
python scripts/validar_cuadro.py
for t in tarifas decreto parser auditoria cuadros explicar deploy limpieza preguntas auth historial paridad; do
  ./venv/Scripts/python.exe pruebas/test_$t.py
done
node --test pruebas-js/*.test.mjs
```

Variables de entorno relevantes: `PORT`, `MODO_PUBLICO`, `AUTH_HABILITADO`,
`AUTH_DB`, `IA_API_URL`, `IA_API_KEY`, `IA_MODELO`, `MAX_HISTORIAL`,
`DIAS_RETENCION_HISTORIAL`, `MAX_PAGINAS_BOLETA`, `RATE_MAX`, `RATE_VENTANA`.

Para desplegar con servidor: `Dockerfile` + `.dockerignore` excluyen
`boletas_reales/`. El sitio recomendado es el estático, ya publicado.

## 12. Decisiones de diseño

1. Sin login por defecto: el sitio público no necesita cuentas. El login de la
   API es opcional y no guarda datos de identidad.
2. Payload mínimo: si se usa IA, viaja solo un JSON validado, nunca el PDF.
3. Cero upload en la versión pública: el análisis ocurre en el navegador.
4. Datos sintéticos en tests: ninguna boleta real entra a los tests ni a git.
5. Explicaciones, no veredictos: siempre se cita la resolución y se recomienda
   pedir el desglose a EJESA.
6. Una sola fuente de verdad para tarifas: `datos/tarifas/*.json`.

## 13. Limitaciones y pendientes

- Actualización trimestral de cuadros; la resolución nov-2026/ene-2027 no está
  cargada. No se afirma que no exista: simplemente no está indexada ni cargada.
- Los `subperiodos` y las `bonificaciones` se documentan con fragmento y fuente
  del Boletín Oficial. Las partidas con origen distinto del decreto vigente no
  se aplican automáticamente: requieren verificación con boleta real.
- Los avisos "a verificar" se eligen por la **resolución aplicada** y citan
  solo fuentes correspondientes a ese cuadro. No calculan diferencias, créditos
  ni saldos y no son veredictos legales.
- El sitio funciona offline después de la primera visita: pdf.js y su worker
  están en `cliente/vendor/pdfjs/` (6.5.438, hashes en el README), las fotos
  son WebP locales y la CSP fija `connect-src 'self'`. Es PWA instalable:
  manifest con rutas relativas, íconos 192/512, service worker cache-first solo
  de assets y versión de caché derivada de datos + UI + fotos. El PDF y los
  datos del usuario nunca se cachean.
- La cabecera y las secciones alternan fondos con fotos de Jujuy; tema claro
  cálido por defecto y oscuro solo si `prefers-color-scheme` lo pide. Las
  fuentes son del sistema y las licencias de las fotos están en
  `cliente/creditos.html`.
- El cliente revisa cargo fijo, uso de red, energía, tarifa social y punitorios
  con su vigencia. La revisión de **plazos de corte** vive en la API
  (`src/decreto.py`), no en el cliente estático.
- Falta la comparación visual de varias boletas del historial local. El botón
  de copiar resumen para WhatsApp ya está implementado.
- La UI de login/historial de la API no está conectada (backend listo).
- Solo se validó el parser con boletas EJESA de los formatos relevados; un PDF
  escaneado no se analiza con OCR: se ofrece la carga manual guiada.

## 14. Glosario

- **kWh**: unidad de consumo de energía eléctrica.
- **Cargo fijo**: monto por tener el servicio, aunque se consuma poco.
- **Uso de red (VAD)**: costo de cables, postes y mantenimiento; se cobra por
  bloques y no cambia dentro del trimestre.
- **Pass through**: actualización del precio de la luz por decisión nacional
  durante el trimestre.
- **Tarifa social**: bonificación del Estado que aparece en un renglón propio.
- **Interés punitorio**: cargo extra por pago tardío, prohibido durante la
  vigencia del Decreto 5658-JG/2026.
- **VAD**: Valor Agregado de Distribución; en la práctica, cargo fijo + uso de
  red.

## 15. Anexo: ecosistema de proyectos

- `cuando-llega-jujuy`: recorridos y paradas de OSM + reportes vecinales de
  frecuencia (https://github.com/MaxxyGuti3rr3z/cuando-llega-jujuy).
- Fichas P1-P5 con ideas derivadas de la exploración (transporte, luz, salud,
  turismo, datos abiertos), fuera de este repositorio.
- Repositorio `jujuy-exploracion`: informe original de la exploración y fuentes
  citadas.

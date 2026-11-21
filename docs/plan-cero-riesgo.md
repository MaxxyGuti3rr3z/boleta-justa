# Plan cero-riesgo para Boleta Justa

Objetivo: que una persona pueda auditar su boleta sin que sus datos salgan de su
dispositivo. Si el dato nunca llega a un servidor, desaparecen de raíz el
storage, los logs, el rate limit, el HTTPS para el PDF y la Ley 25.326 sobre
datos que maneja el proyecto.

## Arquitectura propuesta

```
Navegador (sitio estático, GitHub Pages / Netlify / Cloudflare Pages)
  ├─ pdf.js (CDN) ............ extrae el texto del PDF
  ├─ parser JS ............... port de src/parser_boletas.py
  ├─ auditoría JS ............ port de src/auditoria.py (VAD + bloques)
  ├─ explicación JS .......... port de src/explicar.py
  ├─ cuadros JSON ............ los mismos de datos/tarifas/ (públicos)
  └─ datos del usuario ....... MEMORIA del navegador, nunca se envían
```

No hay backend. La API actual queda como modo local/desarrollo; el deploy
público es solo `web/` + `datos/` + los módulos JS.

## Alternativa sin portar a JS

Pyodide (Python en WASM) permite cargar los `.py` actuales tal cual y pasarle
las líneas extraídas por pdf.js. No se reescribe la lógica, pero el primer
carga pesa ~10-15 MB. Es válida si se quiere una sola fuente de verdad.

## Qué se elimina respecto del deploy con servidor

- `POST /api/auditar` y el archivo temporal en disco del host.
- `GET /api/auditoria` y los parseos del dueño (`boletas_reales/_parseado/`).
- Login / cuentas / sesiones (ver más abajo).
- Rate limit, tope de páginas en servidor, HTTPS para el upload.
- Superficie de ataque del servidor en general.

## Qué queda igual

- Cuadros tarifarios con fuente del Boletín Oficial y vigencia.
- Texto llano, glosario y disclaimer ("orientación vecinal, no dictamen legal").
- Actualización trimestral: es la única tarea de mantenimiento real.

## Decisiones pendientes (a confirmar)

1. **Login**: se recomienda NO agregarlo. Guardar cuentas agrega datos
   personales y aumenta el riesgo, contrario al objetivo. Solo tendría sentido
   para historial entre dispositivos; si se quiere, que sea opcional y con
   datos cifrados en el propio navegador.
2. **Preguntas sobre la boleta**: ya resuelto con `src/payload_ia.py`: se extraen
   los datos localmente y solo viaja un JSON con campos tarifarios permitidos
   (sin nombre, dirección, DNI, CUIT ni números de cuenta). La IA es opcional
   y solo recibe ese payload validado; nunca el PDF. Igualmente, el proveedor
   de IA sí recibe datos financieros anónimos: eso NO es cero-riesgo absoluto,
   pero es el límite acordado. La respuesta por defecto es determinística,
   sin modelo ni llamada externa.

## Orden de trabajo sugerido

1. Port de `parser_boletas.py` a JS + tests con el texto sintético actual.
2. Port de `auditoria.py` (selección por VAD, bloques de uso de red) + tests.
3. Port de `explicar.py` + preguntas determinísticas.
4. Armado del sitio estático y verificación en navegador sin servidor.
5. Publicación en hosting gratuito y baja definitiva del modo servidor.

Hasta que esas decisiones estén confirmadas, el repositorio sigue con el modo
público actual (`MODO_PUBLICO=1`), que es seguro pero todavía recibe el PDF
en el servidor.

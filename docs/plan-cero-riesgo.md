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

1. **Login**: implementado como opcional (`AUTH_HABILITADO=1`, `src/auth.py`).
   Claves con scrypt + salt, email guardado solo como hash, sesiones con token
   opaco (hash en DB, cookie HttpOnly/SameSite/Secure, vencimiento 24 h), límite
   de 5 intentos por IP y cabeceras de seguridad. Sigue desactivado por defecto.
   Es control de acceso: no guarda boletas ni datos de identidad. El historial (`src/historial.py`) guarda SOLO el payload validado
   relacionado con el id interno del usuario: nada de PDFs, emails en claro ni
   datos de identidad, con tope de 50 por usuario y 90 días de retención.
   Si se quiere cifrado en el navegador, ese es el siguiente paso.
2. **Preguntas sobre la boleta**: ya resuelto con `src/payload_ia.py`: se extraen
   los datos localmente y solo viaja un JSON con campos tarifarios permitidos
   (sin nombre, dirección, DNI, CUIT ni números de cuenta). La IA es opcional
   y solo recibe ese payload validado; nunca el PDF. Igualmente, el proveedor
   de IA sí recibe datos financieros anónimos: eso NO es cero-riesgo absoluto,
   pero es el límite acordado. La respuesta por defecto es determinística,
   sin modelo ni llamada externa.

## Estado (actualizado)

1. ✅ Parser a JS (`cliente/parser.js`) con tests `node:test`.
2. ✅ Auditoría a JS (`cliente/auditoria.js`) con selección por VAD y bloques.
3. ✅ Explicación en lenguaje llano (`cliente/explicar.js`).
4. ✅ Sitio estático `cliente/` verificado en navegador con una boleta real:
    fecha, resolución y explicación correctas, y **cero llamadas de red** con
    el PDF durante el análisis (espiando fetch/XHR).
5. ✅ Publicación: https://maxxyguti3rr3z.github.io/boleta-justa-web/

La API local sigue disponible para desarrollo; la versión pública recomendada
es el cliente estático. Las decisiones (sin login, IA solo con payload mínimo)
se mantienen.

(El plan original era: port del parser, port de la auditoría, port de la
explicación, sitio estático y publicación. Esos cinco pasos están hechos salvo
la publicación.)

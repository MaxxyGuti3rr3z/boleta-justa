# Vigilancia del cuadro tarifario

Avisa cuando aparece una señal de que hay un cuadro tarifario nuevo, sin
cargarlo ni modificar `datos/tarifas/`. No extrae importes: solo detecta
números de resolución y fechas de vigencia.

## Cómo funciona

`scripts/vigilar_boletin.py` hace **una sola pasada** por estas tres fuentes:

- búsqueda del Boletín Oficial de Jujuy por `SUSEPU cuadro tarifario`
  (`https://boletinoficial.jujuy.gob.ar/?s=SUSEPU+cuadro+tarifario`); la
  resolución 297 se publicó en `?p=435659`;
- página *Costos del servicio* de EJESA;
- portada de SUSEPU, donde figura *"Cuadro tarifario vigente desde …"*.

Usa solo biblioteca estándar de Python, envía el User-Agent
`boleta-justa-vigilancia`, consulta `robots.txt` una vez por host y hace como
máximo una petición por fuente. Si una fuente falla, lo registra y sigue con
las demás; nunca rompe la ejecución.

La comparación se hace contra la resolución más reciente cargada en
`datos/tarifas/` (hoy, `297-SUSEPU/2026`, vigente hasta el 31/10/2026). Si
encuentra una resolución SUSEPU de cuadro tarifario posterior, o una vigencia
nueva en SUSEPU/EJESA, la marca como novedad. `datos/vigilancia_estado.json`
guarda las claves ya notificadas para no repetir avisos en ejecuciones
posteriores.

El workflow `.github/workflows/vigilancia.yml` corre **todos los lunes a las
09:00 UTC** y también de forma manual (`workflow_dispatch`). Si hay novedades,
abre un issue con título `Posible cuadro tarifario nuevo`, los enlaces
encontrados y esta instrucción:

> Revisar a mano y cargar con docs/como-cargar-un-cuadro.md

Antes de abrirlo busca si ya existe un issue abierto que mencione esa
resolución; si existe, no crea otro. El permiso del workflow es
`issues: write` (más `contents: read` para hacer el checkout). No tiene
`contents: write`: **nunca sube cambios a los cuadros**.

## Pruebas

`pruebas/test_vigilancia.py` usa respuestas simuladas, sin red, para cuatro
casos: sin novedades, resolución nueva, fuente caída y estado ya notificado.
También corre en el workflow de tests.

## Cómo desactivarlo

- En GitHub: *Actions → vigilancia → ⋯ → Disable workflow*. Es lo recomendable
  y no borra nada.
- O quitá el bloque `schedule` de `.github/workflows/vigilancia.yml` para que
  solo pueda ejecutarse a mano.
- Para desactivarlo por completo, eliminá ese workflow. El script queda
  disponible para usarlo localmente con `python scripts/vigilar_boletin.py`.

Si el sitio deja de publicar `robots.txt`, el script sigue (la ausencia se
interpreta como "sin restricciones"). Si `robots.txt` prohíbe una ruta, esa
fuente se marca `bloqueado_por_robots` y no se consulta.

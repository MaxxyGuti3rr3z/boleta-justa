import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CLIENTE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../cliente');
const leer = nombre => readFileSync(path.join(CLIENTE, nombre), 'utf8');

test('textos visibles del historial sin jerga JSON', () => {
  const texto = leer('index.html').replace(/<[^>]*>/g, ' ');
  assert.doesNotMatch(texto, /json/i);
  assert.match(texto, /Guardar copia de seguridad/);
  assert.match(texto, /Recuperar copia de seguridad/);
  assert.match(texto, /Copia de seguridad/);
  assert.match(texto, /Sirve para pasar tu historial a otro celular o no perderlo si borrás los datos del navegador\./);
  assert.match(texto, /Borrar mis análisis/);
  assert.doesNotMatch(texto, /Descargar JSON|Cargar JSON|Borrar todo/);
});

test('diálogo de borrado accesible con el número de análisis', () => {
  const html = leer('index.html');
  assert.match(html, /<dialog id="dialogo-borrar" aria-labelledby="dialogo-borrar-titulo" aria-describedby="dialogo-borrar-mensaje">/);
  assert.match(leer('app.js'), /¿Borrar los \$\{n\} análisis guardados\? No se puede deshacer/);
});

test('respaldo lleva prefijo y fecha en el nombre del archivo', () => {
  assert.match(leer('app.js'),
    /boleta-justa-respaldo-\$\{new Date\(\)\.toISOString\(\)\.slice\(0, 10\)\}\.json/);
});

test('historial colapsa cuando no hay análisis', () => {
  assert.match(leer('app.js'), /\$\('hist-card'\)\.open = items\.length > 0/);
});

test('estado del resultado según el modo de carga', () => {
  const app = leer('app.js');
  const marca = app.indexOf('/* ---------- carga manual');
  assert.ok(marca > 0, 'sección de carga manual presente');
  const antes = app.slice(0, marca);
  const despues = app.slice(marca);
  assert.match(antes, /Leímos tu boleta en tu dispositivo\. Nada se subió ni se guardó\./);
  assert.doesNotMatch(antes, /Datos cargados a mano/);
  assert.match(despues, /Datos cargados a mano\. Nada se subió ni se guardó\./);
});

test('vigencia del cuadro se muestra con nombres de mes', () => {
  const app = leer('app.js');
  assert.match(app, /const ini = MESES\[Number\(mi\) - 1\]/);
  assert.match(app, /\$\{ini} a \$\{fin} de \$\{af\}/);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { calcular } from '../cliente/tarifas.js';
import { auditar } from '../cliente/auditoria.js';
import { TABLAS } from '../cliente/tablas.js';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const CARPETA = path.join(RAIZ, 'pruebas', 'casos_paridad');
const archivos = readdirSync(CARPETA).filter(n => n.endsWith('.json')).sort();

test('existen casos sintéticos de paridad', () => {
  assert.ok(archivos.length >= 20, `solo ${archivos.length} casos`);
});

for (const archivo of archivos) {
  test(`paridad JS: ${archivo}`, () => {
    const caso = JSON.parse(readFileSync(path.join(CARPETA, archivo), 'utf8'));
    const e = caso.entrada;
    let obtenido;
    if (caso.tipo === 'calcular') {
      const { kwh, mes, resolucion, ...opts } = e;
      const tabla = resolucion
        ? TABLAS.find(t => t.resolucion.startsWith(resolucion))
        : undefined;
      obtenido = calcular(kwh, mes || '2026-08', opts, tabla);
    } else if (caso.tipo === 'auditar') {
      obtenido = auditar(e, TABLAS);
    } else {
      assert.fail(`tipo desconocido: ${caso.tipo}`);
    }
    assert.deepEqual(obtenido, caso.esperado);
  });
}

import test from 'node:test';
import assert from 'node:assert/strict';

/* localStorage mínimo para probar el historial sin navegador. */
const almacen = new Map();
globalThis.localStorage = {
  getItem: k => almacen.has(k) ? almacen.get(k) : null,
  setItem: (k, v) => almacen.set(k, String(v)),
  removeItem: k => almacen.delete(k),
};

const hist = await import('../cliente/history.js');
const { construir } = await import('../cliente/payload.js');

const payload = () => construir({
  fecha_emision: '20/08/2026', categoria: 'T1TS',
  energia: { cargo_fijo: 4772, cargo_consumo: 26860, precio_consumo: 141.7971 },
  totales: { a_pagar: 58500 },
}, { estado: 'auditada', resolucion: '297-SUSEPU/2026', cargo_fijo_ok: true });

test('guardar, listar y obtener en el dispositivo', () => {
  almacen.clear();
  const id = hist.guardar(payload());
  const lista = hist.listar();
  assert.equal(lista.length, 1);
  assert.equal(lista[0].mes, '2026-08');
  assert.equal(lista[0].resolucion, '297-SUSEPU/2026');
  assert.equal(hist.obtener(id).categoria, 'T1TS');
});

test('borrado puntual y total', () => {
  almacen.clear();
  const id = hist.guardar(payload());
  hist.guardar(payload());
  assert.equal(hist.listar().length, 2);
  hist.borrar(id);
  assert.equal(hist.listar().length, 1);
  hist.borrarTodo();
  assert.equal(hist.listar().length, 0);
});

test('tope de 20 análisis y export/import', () => {
  almacen.clear();
  for (let i = 0; i < 23; i++) hist.guardar(payload());
  assert.equal(hist.listar().length, 20);
  const json = hist.exportar();
  assert.equal(JSON.parse(json).length, 20);
  hist.borrarTodo();
  assert.equal(hist.importar(json), 20);
  assert.equal(hist.listar().length, 20);
});

test('rechaza importar payload con dato personal', () => {
  almacen.clear();
  const mal = JSON.stringify([{ ...payload(), dni: 12345678 }]);
  assert.throws(() => hist.importar(mal), /no permitidos/);
  assert.equal(hist.listar().length, 0);
});

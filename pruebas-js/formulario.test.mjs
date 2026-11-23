import test from 'node:test';
import assert from 'node:assert/strict';
import { parsear, esTextoUtil } from '../cliente/parser.js';
import { CAMPOS, armarBoleta, validar } from '../cliente/formulario.js';
import { auditar } from '../cliente/auditoria.js';
import { TABLAS } from '../cliente/tablas.js';

const LINEAS = [
  'EVOLUCIÓN DEL CONSUMO EN KWH', '30 Consumo Diario 1500', '30 DÍAS FACTURADOS 30',
  'ENERGÍA ELÉCTRICA', 'Cargo Fijo 4.772,00',
  'Cargo por Consumo de Energía (156.1556 $/kWh) 19.285,22',
  'Cargo por Uso de Red (88.8382 $/kWh) 10.971,52',
  'Bonif. Tarifa Social Provincia -7.417,13',
  'SUBTOTAL ENERGÍA ELÉCTRICA 12.272,81', 'FECHA DE EMISIÓN', '13/02/2026',
  'TOTAL A PAGAR', '30.677,77',
];

const datos = () => ({
  cargoFijo: '4.772,00', precioRed: '88,8382', kwh: '189,5',
  precioEnergia: '141,7971', bonifTS: '-7417,13', periodo: '08/2026',
  fechaEmision: '20/08/2026', punitorios: true,
});

test('detecta PDF sin texto útil (imagen) y texto sí útil', () => {
  assert.equal(esTextoUtil(LINEAS), true);
  assert.equal(esTextoUtil(['', '   ', 'x']), false);
  assert.equal(esTextoUtil(['PK', 'imagen escaneada']), false);
});

test('el formulario produce el MISMO objeto interno que parser.js', () => {
  const boleta = armarBoleta(datos());
  const delParser = parsear(LINEAS);
  assert.deepEqual(Object.keys(boleta).sort(), Object.keys(delParser).sort());
  const clavesEnergia = Object.keys(delParser.energia);
  for (const clave of Object.keys(boleta.energia))
    assert.ok(clavesEnergia.includes(clave), `clave de energía no reconocida: ${clave}`);
  assert.equal(boleta.energia.cargo_fijo, 4772);
  assert.equal(boleta.energia.precio_red, 88.8382);
  assert.equal(boleta.energia.precio_consumo, 141.7971);
  assert.equal(boleta.energia.bonif_tarifa_social, -7417.13);
  assert.equal(boleta.energia.cargo_consumo, Math.round(189.5 * 141.7971 * 100) / 100);
  assert.equal(boleta.fecha_emision, '20/08/2026');
  assert.equal(boleta.punitorios_detectados, true);
  assert.ok(!JSON.stringify(boleta).includes('nombre'));
});

test('funciona con la auditoría existente sin duplicar lógica', () => {
  const r = auditar(armarBoleta(datos()), TABLAS);
  assert.equal(r.estado, 'auditada');
  assert.equal(r.confianza, 'alta');
  assert.ok(r.resolucion.startsWith('227'));
  assert.equal(r.cargo_fijo_ok, true);
});

test('si falta la fecha, se estima desde el período y se aclara', () => {
  const b = armarBoleta({ ...datos(), fechaEmision: '' });
  assert.equal(b.fecha_emision, '01/08/2026');
  assert.match(b.notas.join(' '), /estimada desde el período/);
});

test('errores en lenguaje llano y rangos razonables', () => {
  const faltan = validar({ ...datos(), cargoFijo: '' }).errores.join(' ');
  assert.match(faltan, /Falta completar el cargo fijo/);
  const texto = validar({ ...datos(), precioRed: 'abc' }).errores.join(' ');
  assert.match(texto, /no parece un número/);
  const rango = validar({ ...datos(), kwh: '999999' }).errores.join(' ');
  assert.match(rango, /muy alto o muy bajo/);
  const per = validar({ ...datos(), periodo: '2026' }).errores.join(' ');
  assert.match(per, /formato MM\/AAAA/);
  const fecha = validar({ ...datos(), fechaEmision: '20/09/2026' }).errores.join(' ');
  assert.match(fecha, /no coincide con el período/);
  assert.throws(() => armarBoleta({ ...datos(), kwh: '0' }), /Revisá el número/);
});

test('ayuda por campo y mobile first', () => {
  for (const c of CAMPOS) {
    assert.ok(c.ayuda && c.ayuda.length > 20, `falta ayuda en ${c.clave}`);
    if (c.tipo !== 'checkbox') assert.ok(c.inputmode);
  }
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { construir } from '../cliente/payload.js';
import { tieneSenales, armarReclamo } from '../cliente/reclamo.js';

const boleta = () => ({
  fecha_emision: '20/08/2026', categoria: 'T1TS', dias_facturados: 31.5,
  nombre_titular: 'NO DEBE SALIR', direccion: 'NO DEBE SALIR',
  energia: { cargo_fijo: 4772, cargo_consumo: 26860, precio_consumo: 141.7971,
    precio_red: 88.8382, bonif_tarifa_social: -7417.13 },
  totales: { a_pagar: 58500 },
});
const limpio = {
  estado: 'auditada', resolucion: '297-SUSEPU/2026', cargo_fijo_ok: true,
  uso_red_ok: true, energia_ok: true, energia_diff_pct: 4.2,
  bonif_ts_presente: true, punitorios_signal: false, punitorios_en_vigencia: false,
};

test('sin señales no se ofrece la solicitud', () => {
  const p = construir(boleta(), limpio);
  assert.equal(tieneSenales(p), false);
  assert.equal(armarReclamo(p), '');
});

test('con punitorios se ofrece y cita decreto sin afirmar irregularidad', () => {
  const aud = { ...limpio, punitorios_signal: true, punitorios_en_vigencia: true };
  const p = construir(boleta(), aud);
  assert.equal(tieneSenales(p), true);
  const texto = armarReclamo(p);
  assert.match(texto, /SOLICITUD DE DESGLOSE Y ACLARACIÓN/);
  assert.match(texto, /297-SUSEPU\/2026/);
  assert.match(texto, /Decreto Acuerdo 5658-JG\/2026/);
  assert.match(texto, /Art\. 3\.C/);
  assert.match(texto, /no implica afirmar/);
  assert.match(texto, /\[COMPLETAR/);
  assert.ok(!texto.includes('NO DEBE SALIR'));
  assert.ok(!texto.includes('$'));
});

test('datos escritos a mano aparecen, pero nunca vienen del payload', () => {
  const aud = { ...limpio, cargo_fijo_ok: false };
  const p = construir(boleta(), aud);
  const sinDatos = armarReclamo(p);
  assert.match(sinDatos, /\[COMPLETAR nombre del titular\]/);
  assert.match(sinDatos, /\[COMPLETAR número de suministro\]/);
  const conDatos = armarReclamo(p, { nombre: 'Vecina Prueba', suministro: '123' });
  assert.match(conDatos, /Vecina Prueba/);
  assert.match(conDatos, /N° 123/);
  assert.match(conDatos, /El cargo fijo/);
});

test('rechaza payload con campos fuera de la lista blanca', () => {
  const aud = { ...limpio, cargo_fijo_ok: false };
  const p = { ...construir(boleta(), aud), dni: 12345678 };
  assert.throws(() => tieneSenales(p), /no permitidos/);
  assert.throws(() => armarReclamo(p), /no permitidos/);
});

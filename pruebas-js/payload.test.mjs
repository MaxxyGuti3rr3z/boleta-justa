import test from 'node:test';
import assert from 'node:assert/strict';
import { construir, validar } from '../cliente/payload.js';

const boleta = {
  fecha_emision: '20/08/2026', categoria: 'T1TS', dias_facturados: 31.5,
  nombre_titular: 'NO DEBE SALIR', domicilio: 'NO DEBE SALIR',
  energia: { cargo_fijo: 4772, cargo_consumo: 26860, precio_consumo: 141.7971,
    precio_red: 88.8382, bonif_tarifa_social: -7417.13 },
  impuestos: { iva_consumidor: 4155.82, subtotal: 9843.9 },
  agua: { iva_punitorio: 430.54 }, totales: { a_pagar: 58500 },
};
const aud = {
  estado: 'auditada', resolucion: '297-SUSEPU/2026', categoria_tabla: 'R1',
  cargo_fijo_ok: true, uso_red_ok: true, energia_ok: false, energia_diff_pct: 4.2,
  bonif_ts_presente: true, punitorios_signal: true, punitorios_en_vigencia: true,
};

test('payload del cliente solo tiene campos tarifarios', () => {
  const p = construir(boleta, aud);
  validar(p);
  assert.ok(!JSON.stringify(p).includes('NO DEBE SALIR'));
  assert.ok(!('nombre_titular' in p));
  assert.equal(p.mes, '2026-08');
  assert.equal(p.consumo_kwh, 189.4);
  assert.equal(p.auditoria.resolucion, '297-SUSEPU/2026');
});

test('valida rechaza campos extra y datos personales', () => {
  const p = construir(boleta, aud);
  assert.throws(() => validar({ ...p, dni: 12345678 }), /no permitidos/);
  assert.throws(() => validar({ ...p, notas: 'Juan Pérez DNI 12345678' }), /dato personal|no permitidos/);
});

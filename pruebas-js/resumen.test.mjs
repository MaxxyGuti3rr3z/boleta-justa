import test from 'node:test';
import assert from 'node:assert/strict';
import { construir } from '../cliente/payload.js';
import { armarResumen, enlaceWhatsApp } from '../cliente/resumen.js';

const boleta = () => ({
  fecha_emision: '20/08/2026', categoria: 'T1TS', dias_facturados: 31.5,
  nombre_titular: 'NO DEBE SALIR', direccion: 'NO DEBE SALIR',
  energia: { cargo_fijo: 4772, cargo_consumo: 26860, precio_consumo: 141.7971,
    precio_red: 88.8382, bonif_tarifa_social: -7417.13 },
  impuestos: { iva_consumidor: 4155.82 }, totales: { a_pagar: 58500 },
});
const baseAud = {
  estado: 'auditada', resolucion: '297-SUSEPU/2026', cargo_fijo_ok: true,
  uso_red_ok: true, energia_ok: true, bonif_ts_presente: true,
  punitorios_signal: false, punitorios_en_vigencia: false,
};

test('resumen es corto, cita el cuadro y no filtra datos personales', () => {
  const texto = armarResumen(construir(boleta(), baseAud));
  assert.ok(texto.length < 900, 'menos de 900 caracteres');
  assert.match(texto, /2026-08/);
  assert.match(texto, /297-SUSEPU\/2026/);
  assert.match(texto, /Coincide:/);
  assert.match(texto, /orientación, no un veredicto/);
  assert.ok(!texto.includes('NO DEBE SALIR'));
  assert.ok(!texto.includes('$'), 'sin importes');
});

test('resumen explica el pass through y los punitorios con prudencia', () => {
  const aud = { ...baseAud, energia_ok: false, energia_diff_pct: 4.2,
    punitorios_signal: true, punitorios_en_vigencia: true };
  const texto = armarResumen(construir(boleta(), aud));
  assert.match(texto, /4,2%/);
  assert.match(texto, /actualización del trimestre/);
  assert.match(texto, /conviene pedir el desglose/);
  assert.doesNotMatch(texto, /irregularidad/);
});

test('resumen sin cuadro avisa y no inventa resolución de reclamo', () => {
  const aud = { estado: 'cuadro_no_disponible', resolucion: null };
  const texto = armarResumen(construir(boleta(), aud));
  assert.match(texto, /Todavía no tenemos cargado el cuadro tarifario/);
  assert.match(texto, /orientación, no un veredicto/);
  assert.doesNotMatch(texto, /Coincide:/);
});

test('enlace de WhatsApp codifica el mismo resumen', () => {
  const texto = armarResumen(construir(boleta(), baseAud));
  const enlace = enlaceWhatsApp(texto);
  assert.ok(enlace.startsWith('https://wa.me/?text='));
  assert.equal(decodeURIComponent(enlace.split('?text=')[1]), texto);
});

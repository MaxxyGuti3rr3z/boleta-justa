import test from 'node:test';
import assert from 'node:assert/strict';
import { explicar } from '../cliente/explicar.js';

function aud() {
  return {
    estado: 'auditada', mes: '2026-08', resolucion: '297-SUSEPU/2026',
    cargo_fijo_ok: true, uso_red_ok: true, bonif_ts_presente: true,
    energia_ok: false, energia_diff_pct: 4.2, punitorios_signal: true,
    punitorios_en_vigencia: true, categoria_boleta: 'T1TS',
  };
}

test('explicación en lenguaje llano con mes natural y glosario', () => {
  const x = explicar(aud());
  assert.match(x.titulo, /agosto de 2026/);
  assert.equal(x.estado, 'a_revisar');
  assert.ok(x.items.length >= 4);
  assert.equal(x.glosario.length, 6);
  const textos = x.items.map(i => i.texto).join(' ');
  assert.match(textos, /4\.2%/);
  assert.match(textos, /no significa un error/);
  assert.match(textos, /Decreto 5658/);
});

test('sin cuadro disponible avisa en lenguaje llano y no da veredicto', () => {
  const x = explicar({ estado: 'cuadro_no_disponible', mes: '2026-12',
    mensaje: 'Todavía no tenemos cargado el cuadro tarifario de este período, así que no podemos compararlo. Podés pedirle a EJESA el desglose.' });
  assert.equal(x.estado, 'sin_cuadro');
  assert.match(x.resumen, /Todavía no tenemos cargado el cuadro tarifario/);
  assert.match(x.resumen, /pedirle a EJESA el desglose/);
  assert.ok(!x.items.some(i => i.icono === '⚠️'));
  assert.match(x.items[0].texto, /no podemos afirmar/);
});

test('sin datos devuelve estado sin_datos', () => {
  assert.equal(explicar({ estado: 'sin_cuadro_cargado' }).estado, 'sin_datos');
});

test('suma inconsistente se explica', () => {
  const x = explicar(aud(), { consistencia: { coincide_a_pagar: false } });
  assert.ok(x.items.some(i => i.titulo.includes('suma no cierra')));
});

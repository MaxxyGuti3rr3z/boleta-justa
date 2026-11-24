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

test('total no verificable no cuenta como señal', () => {
  const limpia = { ...aud(), energia_ok: true, energia_diff_pct: 0,
    punitorios_signal: false, punitorios_en_vigencia: false };
  const x = explicar(limpia, { consistencia: { coincide_a_pagar: false } });
  assert.ok(x.items.some(i => i.titulo.includes('No pudimos verificar el total')));
  assert.ok(!x.items.some(i => i.icono === '⚠️' && i.titulo.includes('total')));
  assert.equal(x.estado, 'en_orden');
});

test('avisos a verificar no cambian el estado y siguen al cuadro aplicado', () => {
  const limpia = { ...aud(), mes: '2026-03', energia_ok: true, energia_diff_pct: 0,
    punitorios_signal: false, punitorios_en_vigencia: false };
  const x = explicar(limpia);
  assert.equal(x.estado, 'en_orden');
  const avisos = x.items.filter(i => i.clave);
  assert.equal(avisos.length, 1);
  assert.equal(avisos[0].clave, '297');
  assert.ok(avisos[0].fuentes.some(f => f.includes('297-SUSEPU/2026')));
  const sinNota = explicar({ ...limpia, resolucion: '168-SUSEPU/2025' });
  assert.ok(!sinNota.items.some(i => i.clave));
});

test('las fuentes del aviso corresponden al cuadro aplicado', () => {
  const base = { ...aud(), energia_ok: true, energia_diff_pct: 0,
    punitorios_signal: false, punitorios_en_vigencia: false };
  const con227 = explicar({ ...base, resolucion: '227-SUSEPU/2026', mes: '2026-08' });
  const a227 = con227.items.find(i => i.clave === '227');
  assert.ok(a227);
  const fuentes227 = a227.fuentes.join(' ');
  assert.match(fuentes227, /227-SUSEPU\/2026/);
  assert.doesNotMatch(fuentes227, /476-SUSEPU|105-SUSEPU|104-SUSEPU/);
  const con81 = explicar({ ...base, resolucion: '81-SUSEPU/2026', mes: '2026-03' });
  const a81 = con81.items.find(i => i.clave === '81');
  assert.ok(a81);
  assert.match(a81.fuentes.join(' '), /104-SUSEPU\/2026/);
});

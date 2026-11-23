import test from 'node:test';
import assert from 'node:assert/strict';
import { TABLAS } from '../cliente/tablas.js';
import { auditar, seleccionarTabla, precioRedPorBloques, mesDe, cercana,
  MENSAJE_CUADRO_NO_DISPONIBLE } from '../cliente/auditoria.js';

const cats = TABLAS.find(t => t.resolucion.startsWith('227')).t1_residencial.categorias;
const redBloques = precioRedPorBloques(cats, 189.5);

function boleta() {
  return {
    fecha_emision: '20/08/2026', categoria: 'T1TS', punitorios_detectados: true,
    energia: {
      cargo_fijo: 4772, cargo_consumo: 189.5 * 141.0, precio_consumo: 141.0,
      precio_red: redBloques, cargo_red: redBloques * 189.5,
      bonif_tarifa_social: -7417.13,
    },
  };
}

test('hay 6 cuadros oficiales y el mes se normaliza', () => {
  assert.equal(TABLAS.length, 6);
  assert.equal(mesDe('20/08/2026'), '2026-08');
  assert.equal(mesDe(null), null);
});

test('selecciona el cuadro por VAD, no por fecha de emisión', () => {
  const b = boleta();
  const { tabla, score, confianza } = seleccionarTabla(b, TABLAS);
  assert.ok(tabla.resolucion.startsWith('227'));
  assert.ok(score < 1);
  assert.equal(confianza, 'alta');
});

test('auditoría: cargo fijo y uso de red por bloques coinciden', () => {
  const r = auditar(boleta(), TABLAS);
  assert.equal(r.estado, 'auditada');
  assert.equal(r.cargo_fijo_ok, true);
  assert.equal(r.uso_red_ok, true);
  assert.equal(r.uso_red_metodo, 'bloques');
  assert.equal(r.bonif_ts_presente, true);
  assert.equal(r.resolucion_por_fecha.startsWith('297'), true);
});

test('punitorios solo sealan dentro de la vigencia del Decreto 5658', () => {
  const vigente = auditar({ ...boleta(), fecha_emision: '05/08/2026' }, TABLAS);
  const anterior = auditar({ ...boleta(), fecha_emision: '05/02/2026' }, TABLAS);
  assert.equal(vigente.punitorios_en_vigencia, true);
  assert.equal(anterior.punitorios_en_vigencia, false);
});

test('VAD sin coincidencia: estado explícito, sin cuadro más cercano', () => {
  const rara = {
    fecha_emision: '05/12/2026', categoria: 'T1TS',
    energia: { cargo_fijo: 999999, precio_red: 777.7777,
      cargo_consumo: 100, precio_consumo: 200 },
  };
  const { tabla, confianza } = seleccionarTabla(rara, TABLAS);
  assert.equal(tabla, null);
  assert.equal(confianza, 'baja');
  const r = auditar(rara, TABLAS);
  assert.equal(r.estado, 'cuadro_no_disponible');
  assert.equal(r.resolucion, null);
  assert.equal(r.confianza, 'baja');
  assert.ok(r.score_vad_pct > 3);
  assert.equal(r.mensaje, MENSAJE_CUADRO_NO_DISPONIBLE);
});

test('sin datos VAD devuelve estado explícito y cercana usa tolerancia relativa', () => {
  const r = auditar({ fecha_emision: '05/08/2026', energia: {} }, TABLAS);
  assert.equal(r.estado, 'sin_cuadro_cargado');
  assert.ok(cercana(cats, 'uso_red_kwh', cats[0].uso_red_kwh + 0.01));
});

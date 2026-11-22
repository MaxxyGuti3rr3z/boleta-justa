import test from 'node:test';
import assert from 'node:assert/strict';
import { parsear } from '../cliente/parser.js';

/* Texto SINTÉTICO (idéntico al de pruebas/test_parser.py). Nunca boletas reales. */
const TEXTO = `
EVOLUCIÓN DEL CONSUMO EN KWH
30 Consumo Diario 1500
30 Días Facturados 30
ENERGÍA ELÉCTRICA
Cargo Fijo 4.772,00
Cargo por Consumo de Energía (156.1556 $/kWh) 19.285,22
Cargo por Uso de Red (88.8382 $/kWh) 10.971,52
Subsidio Estado Nacional – N2 -6.604,57
Bonif. Tarifa Social Provincia -6.250,08
SUBTOTAL ENERGÍA ELÉCTRICA 12.272,81
TASAS E IMPUESTOS
Percep. contrib. única (6%) 736,37
Tasa Fiscalización Susepu 1.5% 402,34
Percep.Alumbrado Publico 3.979,52
IVA Consumidor Final 5.632,79
IVA Intereses % 1.005,94
SUBTOTAL TASAS E IMPUESTOS 11.756,96
OTROS CARGOS
Cargo FOPEJ Res 7-ISPTyV-22 (0,1500 $/kWh) 30,00
Ajuste por Redondeo - Resoluc. N° 48-SUSEPU-25 -12,00
SUBTOTAL OTROS CARGOS 18,00
TOTAL EJESA 24.047,77
EVOLUCIÓN DEL CONSUMO EN M3 SERVICIOS SANITARIOS
Cargo Variable Agua 4,50
Cargo Fijo 3.747,90
TASAS E IMPUESTOS
Iva 21 % 985,54
IVA Interés Punitorio 21% 102,04
SUBTOTAL TASAS E IMPUESTOS 1.245,41
TOTAL 6.630,00
FECHA DE EMISIÓN
13/02/2026
VENCIMIENTO
03/03/2026
TOTAL A PAGAR
30.677,77
`;

const lineas = TEXTO.split('\n').map(l => l.trim()).filter(Boolean);

test('parser extrae campos tarifarios con coma decimal y precio con punto', () => {
  const d = parsear(lineas);
  assert.equal(d.energia.cargo_fijo, 4772);
  assert.equal(d.energia.precio_consumo, 156.1556);
  assert.equal(d.energia.precio_red, 88.8382);
  assert.equal(d.energia.bonif_tarifa_social, -6250.08);
  assert.equal(d.impuestos.iva_consumidor, 5632.79);
  assert.equal(d.agua.iva_punitorio, 102.04);
  assert.equal(d.punitorios_detectados, true);
  assert.equal(d.totales.a_pagar, 30677.77);
});

test('parser respeta secciones (el cargo fijo de agua no pisa el de luz)', () => {
  const d = parsear(lineas);
  assert.equal(d.energia.cargo_fijo, 4772);
  assert.equal(d.agua.cargo_fijo, 3747.9);
});

test('parser lee fechas y detecta consistencia sin exponer datos personales', () => {
  const d = parsear(lineas);
  assert.equal(d.fecha_emision, '13/02/2026');
  assert.equal(d.vencimiento, '03/03/2026');
  assert.equal(d.consistencia.coincide_a_pagar, true);
  assert.ok(!JSON.stringify(d).match(/dni|domicilio|titular/i));
});

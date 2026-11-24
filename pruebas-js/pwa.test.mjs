import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CLIENTE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../cliente');
const leer = nombre => readFileSync(path.join(CLIENTE, nombre), 'utf8');

test('manifest instalable con rutas relativas al subpath', () => {
  const m = JSON.parse(leer('manifest.webmanifest'));
  assert.ok(m.name && m.short_name);
  assert.equal(m.start_url, './');
  assert.equal(m.scope, './');
  assert.equal(m.display, 'standalone');
  assert.equal(m.theme_color, '#F7F1E6');
  assert.equal(m.icons.length, 2);
  for (const icono of m.icons) {
    assert.ok(icono.src.startsWith('./icons/'), `ícono no relativo: ${icono.src}`);
    assert.equal(icono.type, 'image/png');
    assert.ok(existsSync(path.join(CLIENTE, icono.src.slice(2))));
  }
});

test('íconos tienen 192 y 512 píxeles', () => {
  for (const [nombre, esperado] of [['icon-192.png', 192], ['icon-512.png', 512]]) {
    const buf = readFileSync(path.join(CLIENTE, 'icons', nombre));
    assert.equal(buf.readUInt32BE(16), esperado);
    assert.equal(buf.readUInt32BE(20), esperado);
  }
});

test('service worker solo cachea assets estáticos, nunca PDF ni datos del usuario', () => {
  const sw = leer('sw.js');
  assert.match(sw, /const ASSETS = \[/);
  assert.match(sw, /cache: 'no-store'/);
  assert.match(sw, /NEW_VERSION/);
  assert.match(sw, /SKIP_WAITING/);
  assert.ok(!/api\/auditar|arrayBuffer|FileReader|localStorage|indexedDB/.test(sw));
  const lista = sw.slice(sw.indexOf('['), sw.indexOf('];') + 1);
  for (const permitido of ['index.html', 'app.js', 'tablas.js', 'version.json',
    'pdf.min.js', 'pdf.worker.min.js', 'icon-192.png'])
    assert.ok(lista.includes(permitido), `falta en ASSETS: ${permitido}`);
  assert.ok(!/\.pdf'|\.pdf"/.test(lista), 'no debe cachear PDFs');
});

test('versión de cuadros explícita y consistente', () => {
  const v = JSON.parse(leer('version.json'));
  assert.match(v.cache, /^boleta-justa-[0-9a-f]{12}$/);
  assert.equal(v.cache, `boleta-justa-${v.cuadros_hash}`);
  assert.match(v.actualizado, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(v.resoluciones.length, 6);
  const html = leer('index.html');
  assert.match(html, /id="version-cuadros"/);
  assert.match(html, /id="update-banner"/);
  assert.match(html, /rel="manifest" href="\.\/manifest\.webmanifest"/);
  assert.match(html, /default-src 'self'/);
});

test('aviso de nueva versión exige una versión instalada previamente', () => {
  const sw = leer('sw.js');
  assert.match(sw, /version-instalada\.json/);
  assert.match(sw, /c\.put\(destino\('\.\/version-instalada\.json'\)/);
  const inicio = sw.indexOf("if (tipo === 'CHECK_VERSION')");
  const fin = sw.indexOf("if (tipo === 'SKIP_WAITING')");
  assert.ok(inicio >= 0 && fin > inicio, 'bloque CHECK_VERSION presente');
  const bloque = sw.slice(inicio, fin);
  assert.match(bloque, /instalada = marca \? await marca\.json\(\) : null/);
  assert.match(bloque, /instalada && instalada\.cache !== version\.cache/);
  const app = leer('app.js');
  assert.match(app, /NEW_VERSION/);
  assert.match(app, /update-banner/);
});

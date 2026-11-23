import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CLIENTE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../cliente');
const leer = nombre => readFileSync(path.join(CLIENTE, nombre), 'utf8');
const URLS = /https?:\/\/[^\s"'`)]+/g;

test('index.html y módulos propios no contienen URLs externas', () => {
  const archivos = ['index.html', 'app.js', 'parser.js', 'auditoria.js',
    'explicar.js', 'payload.js', 'history.js', 'formulario.js', 'reclamo.js', 'tarifas.js'];
  for (const nombre of archivos) {
    const encontradas = leer(nombre).match(URLS) || [];
    assert.deepEqual(encontradas, [], `${nombre} contiene URLs externas: ${encontradas}`);
  }
});

test('tablas.js solo contiene URLs de citas del Boletín Oficial', () => {
  const urls = leer('tablas.js').match(URLS) || [];
  for (const url of urls)
    assert.ok(url.startsWith('https://boletinoficial.jujuy.gob.ar/'),
      `URL no permitida en tablas.js: ${url}`);
});

test('todo recurso referenciado en index.html es relativo', () => {
  const html = leer('index.html');
  const refs = [...html.matchAll(/(?:src|href)\s*=\s*["']([^"']+)["']/g)].map(m => m[1]);
  assert.ok(refs.length > 0);
  for (const ref of refs)
    assert.ok(!/^(?:https?:)?\/\//.test(ref), `recurso externo: ${ref}`);
});

test('CSP bloquea conexiones, scripts de terceros y formularios externos', () => {
  const html = leer('index.html');
  assert.match(html, /http-equiv="Content-Security-Policy"/);
  assert.match(html, /connect-src 'self'/);
  assert.match(html, /form-action 'self'/);
  assert.match(html, /script-src 'self'/);
  assert.match(html, /worker-src 'self'/);
  assert.doesNotMatch(html, /script-src[^;]*https?:/);
});

test('app.js carga pdf.js y su worker desde la carpeta local', () => {
  const app = leer('app.js');
  assert.match(app, /from '\.\/vendor\/pdfjs\/pdf\.min\.js'/);
  assert.match(app, /new URL\('\.\/vendor\/pdfjs\/pdf\.worker\.min\.js', import\.meta\.url\)/);
  assert.doesNotMatch(app, /cdn\.jsdelivr|unpkg\.com|https?:\/\//);
});

test('enlace wa.me es solo un enlace voluntario en resumen.js', () => {
  const urls = leer('resumen.js').match(URLS) || [];
  for (const url of urls)
    assert.ok(url.startsWith('https://wa.me/?text='), `URL no permitida en resumen.js: ${url}`);
  const reclamoUrls = leer('reclamo.js').match(URLS) || [];
  assert.deepEqual(reclamoUrls, []);
});

test('vendor completo, con LICENSE, README y hashes verificados', () => {
  const esperados = {
    'pdf.min.js': '3a88402882cfa3e7e72c2c9b5149f52f0f88baf1c5b62aa11a41abdbc2072440',
    'pdf.worker.min.js': '1e64c8240e54735ec5913b37acd5134747799cb8c6bb3777c70adbc01232d2aa',
    'LICENSE': '0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594',
  };
  for (const [nombre, hash] of Object.entries(esperados)) {
    const ruta = path.join(CLIENTE, 'vendor', 'pdfjs', nombre);
    assert.ok(existsSync(ruta), `falta ${nombre}`);
    const real = createHash('sha256').update(readFileSync(ruta)).digest('hex');
    assert.equal(real, hash, `hash incorrecto: ${nombre}`);
  }
  const readme = leer(path.join('vendor', 'pdfjs', 'README.md'));
  assert.match(readme, /6\.5\.438/);
  assert.match(readme, /Apache-2\.0/);
});

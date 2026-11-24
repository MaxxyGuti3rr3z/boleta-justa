import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const CLIENTE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../cliente');
const URL = pathToFileURL(path.join(CLIENTE, 'index.html')).href;

const CANDIDATOS = [
  process.env.CHROME_PATH,
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
].filter(Boolean);

const chrome = CANDIDATOS.find(p => existsSync(p));
const sleep = ms => new Promise(r => setTimeout(r, ms));

test('layout centrado sin scroll horizontal en varios anchos, zoom y modos de color', { skip: chrome ? false : 'Chrome no disponible' }, async () => {
  const puerto = 9300 + Math.floor(Math.random() * 500);
  const perfil = mkdtempSync(path.join(tmpdir(), 'bj-layout-'));
  const proc = spawn(chrome, [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--allow-file-access-from-files', '--no-sandbox',
    `--remote-debugging-port=${puerto}`, `--user-data-dir=${perfil}`, '--window-size=1280,900', 'about:blank',
  ], { stdio: 'ignore' });

  let ws;
  try {
    let target;
    for (let i = 0; i < 40; i++) {
      try {
        const lista = await (await fetch(`http://127.0.0.1:${puerto}/json/list`)).json();
        target = lista.find(t => t.type === 'page');
        if (target) break;
      } catch {}
      await sleep(250);
    }
    assert.ok(target, 'Chrome expuso un target de página');

    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    let id = 0;
    const pendientes = new Map();
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pendientes.has(m.id)) { pendientes.get(m.id)(m); pendientes.delete(m.id); }
    };
    const send = (method, params = {}) => new Promise(res => {
      const n = ++id;
      pendientes.set(n, res);
      ws.send(JSON.stringify({ id: n, method, params }));
    });
    const medir = async () => {
      const r = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
        const d = document.documentElement;
        const w = document.querySelector('.wrap').getBoundingClientRect();
        return { scrollWidth: d.scrollWidth, clientWidth: d.clientWidth,
          izq: Math.round(w.left), der: Math.round(d.clientWidth - w.right) };
      })()` });
      return r.result.result.value;
    };

    for (const esquema of ['light', 'dark']) {
      await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: esquema }] });
      for (const ancho of [360, 768, 1280, 1920, 2560, 3840]) {
        await send('Emulation.setDeviceMetricsOverride', { width: ancho, height: 900, deviceScaleFactor: 1, mobile: ancho <= 768 });
        await send('Page.navigate', { url: URL });
        await sleep(350);
        const m = await medir();
        assert.ok(m.scrollWidth <= m.clientWidth + 1,
          `${esquema} ${ancho}px: scroll horizontal ${m.scrollWidth} > ${m.clientWidth}`);
        assert.ok(Math.abs(m.izq - m.der) <= 2,
          `${esquema} ${ancho}px: contenedor descentrado (${m.izq} vs ${m.der})`);
      }
      for (const ancho of [360, 768]) {
        await send('Emulation.setDeviceMetricsOverride', { width: ancho, height: 900, deviceScaleFactor: 1, mobile: true });
        await send('Page.navigate', { url: URL });
        await sleep(350);
        await send('Runtime.evaluate', { expression: `document.getElementById('borrar-todo').click()` });
        await sleep(200);
        const d = (await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
          const e = document.getElementById('dialogo-borrar');
          const r = e.getBoundingClientRect();
          return { abierto: e.open, left: Math.round(r.left), right: Math.round(r.right),
            top: Math.round(r.top), bottom: Math.round(r.bottom),
            clientWidth: document.documentElement.clientWidth, innerHeight: window.innerHeight };
        })()` })).result.result.value;
        assert.ok(d.abierto, `${esquema} ${ancho}px: el diálogo no se abrió`);
        assert.ok(d.left >= 0 && d.right <= d.clientWidth + 1,
          `${esquema} ${ancho}px: diálogo excede el ancho (${d.left}..${d.right} vs ${d.clientWidth})`);
        assert.ok(d.top >= 0 && d.bottom <= d.innerHeight + 1,
          `${esquema} ${ancho}px: diálogo excede la altura (${d.top}..${d.bottom} vs ${d.innerHeight})`);
      }

      await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
      await send('Page.navigate', { url: URL });
      await sleep(350);
      for (const factor of [1.25, 2]) {
        await send('Emulation.setPageScaleFactor', { pageScaleFactor: factor });
        await sleep(250);
        const m = await medir();
        assert.ok(m.scrollWidth <= m.clientWidth + 1, `${esquema} zoom ${factor}: scroll horizontal`);
        assert.ok(Math.abs(m.izq - m.der) <= 2, `${esquema} zoom ${factor}: contenedor descentrado (${m.izq} vs ${m.der})`);
      }
      await send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });
    }
  } finally {
    if (ws) ws.close();
    proc.kill('SIGKILL');
  }
});

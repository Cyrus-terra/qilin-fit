import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Script, createContext } from 'node:vm';

// Synthetic DOM regression checks only: no browser rendering, real IME, GPU,
// enterprise-policy enforcement or real-device compatibility is verified here.
const assets = new URL('../skills/qilin-fit/assets/', import.meta.url);
const html = readFileSync(new URL('browser-probe.html', assets), 'utf8');
const inlineScripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)];
assert.equal(inlineScripts.length, 1, 'the offline probe has one inline script');
const source = inlineScripts[0][1];
const probeScript = new Script(source, { filename: 'browser-probe.inline.js' });
const reviewIds = ['review-colors', 'review-dialog', 'review-ime', 'review-layout', 'review-dark', 'review-webgl'];

function boot(options = {}) {
  const elements = Object.create(null);
  const listeners = Object.create(null);
  const calls = { forbidden: [], blobs: [], downloads: [], revoked: [], timers: [] };
  let document;

  function forbidden(name) {
    return function () {
      calls.forbidden.push(name);
      throw new Error('Forbidden probe action: ' + name);
    };
  }
  function unreadable(object, key, name = key) {
    Object.defineProperty(object, key, { get: forbidden(name), configurable: true });
  }
  function element(tagName, id = '') {
    const node = {
      tagName, id, value: '', className: '', style: {}, children: [],
      textContent: '', attributes: {}, parentNode: null,
      get firstChild() { return this.children[0] || null; },
      appendChild(child) {
        assert.equal(child.parentNode, null);
        this.children.push(child);
        child.parentNode = this;
        return child;
      },
      removeChild(child) {
        const index = this.children.indexOf(child);
        assert.notEqual(index, -1);
        this.children.splice(index, 1);
        child.parentNode = null;
        return child;
      },
      setAttribute(key, value) { this.attributes[key] = String(value); },
      contains(child) {
        return this === child || this.children.some(item => item.contains(child));
      },
      focus() {
        document.activeElement = this;
        for (const listener of listeners.focusin || []) listener({ target: this });
      },
      click() {
        if (this.tagName === 'a') {
          assert.match(this.href, /^blob:/, 'only a local Blob URL may be downloaded');
          calls.downloads.push({ href: this.href, filename: this.download });
        }
        if (this.onclick) this.onclick();
      }
    };
    Object.defineProperty(node, 'innerHTML', {
      get: forbidden('innerHTML read'), set: forbidden('innerHTML write')
    });
    return node;
  }

  for (const match of html.matchAll(/<([a-z][a-z0-9-]*)\b[^>]*\bid="([^"]+)"[^>]*>/gi)) {
    assert.equal(elements[match[2]], undefined, 'unique element ids');
    elements[match[2]] = element(match[1].toLowerCase(), match[2]);
  }
  document = {
    body: element('body'),
    documentElement: { clientWidth: 1024, clientHeight: 768 },
    activeElement: null,
    getElementById(id) {
      assert.ok(elements[id], 'known DOM id: ' + id);
      return elements[id];
    },
    createElement(tagName) {
      assert.ok(['a', 'tr', 'td'].includes(tagName), 'no active/resource element creation');
      return element(tagName);
    },
    addEventListener(name, callback) {
      (listeners[name] || (listeners[name] = [])).push(callback);
    }
  };
  elements.overlay.appendChild(elements['dialog-panel']);
  elements['dialog-panel'].appendChild(elements['dialog-confirm']);
  elements['dialog-panel'].appendChild(elements['dialog-close']);
  for (const id of reviewIds) elements[id].value = 'unknown';
  unreadable(elements['ime-input'], 'value', 'IME value');
  unreadable(elements['ime-input'], 'textContent', 'IME textContent');
  unreadable(document, 'cookie', 'cookie read');

  function BlobMock(parts, config) {
    this.text = parts.join('');
    this.type = config.type;
    calls.blobs.push(this);
  }
  function CanvasMock() { forbidden('canvas construction')(); }
  CanvasMock.prototype.getContext = forbidden('GPU/canvas context');
  const window = {
    Blob: BlobMock,
    URL: {
      createObjectURL(blob) {
        assert.ok(blob instanceof BlobMock);
        return 'blob:synthetic-probe-download';
      },
      revokeObjectURL(url) { calls.revoked.push(url); }
    },
    HTMLCanvasElement: CanvasMock,
    WebGLRenderingContext: forbidden('WebGL constructor'),
    WebGL2RenderingContext: forbidden('WebGL2 constructor'),
    innerWidth: 1024, innerHeight: 768, devicePixelRatio: 1.25,
    isSecureContext: false,
    getComputedStyle() { return { backgroundColor: 'rgb(64, 184, 130)' }; },
    setTimeout(callback) { calls.timers.push(callback); },
    fetch: forbidden('fetch'), XMLHttpRequest: forbidden('XMLHttpRequest'),
    WebSocket: forbidden('WebSocket'), EventSource: forbidden('EventSource'),
    Worker: forbidden('Worker'), SharedWorker: forbidden('SharedWorker'),
    RTCPeerConnection: forbidden('RTCPeerConnection')
  };
  for (const name of ['localStorage', 'sessionStorage', 'indexedDB']) unreadable(window, name);
  const navigator = {
    userAgent: 'synthetic-test-not-device-evidence',
    platform: 'synthetic-platform', language: 'zh-CN',
    sendBeacon: forbidden('sendBeacon')
  };
  for (const name of ['storage', 'serviceWorker', 'permissions', 'geolocation']) unreadable(navigator, name);
  if (options.hints) {
    navigator.userAgentData = {
      brands: [{ brand: 'Synthetic', version: '0' }], mobile: false,
      platform: 'synthetic-hints-platform',
      getHighEntropyValues: forbidden('high entropy Client Hints')
    };
  }
  if (options.css) window.CSS = options.css;
  if (options.noBlob) window.Blob = undefined;
  const context = createContext({
    ...window, window, document, navigator,
    eval: forbidden('eval'), Function: forbidden('Function constructor')
  }, { codeGeneration: { strings: false, wasm: false } });
  probeScript.runInContext(context, { timeout: 1000 });

  return {
    elements, document, window, calls,
    environment() { return JSON.parse(elements.environment.textContent); },
    exportReport() {
      const count = calls.blobs.length;
      elements.export.click();
      assert.equal(calls.blobs.length, count + 1, 'one Blob per explicit export click');
      return JSON.parse(calls.blobs.at(-1).text);
    },
    key(code, shiftKey = false) {
      let prevented = false;
      const event = { keyCode: code, shiftKey, preventDefault() { prevented = true; } };
      for (const listener of listeners.keydown || []) listener(event);
      return prevented;
    }
  };
}

test('synthetic only: matrix is valid, unfilled and provisional', () => {
  const matrix = JSON.parse(readFileSync(new URL('support-matrix.example.json', assets), 'utf8'));
  assert.equal(matrix.schemaVersion, 1);
  assert.equal(matrix.status, 'unknown');
  assert.deepEqual(matrix.environments, []);
  assert.deepEqual(matrix.environmentTemplate.results, []);
  assert.equal(matrix.environmentTemplate.overall, 'unknown');
  assert.equal(matrix.resultTemplate.status, 'unknown');
  assert.deepEqual(matrix.baselineChromium.version, 102);
  assert.equal(matrix.baselineChromium.status, 'provisional');
  assert.equal(matrix.baselineChromium.requiresConfirmation, true);
  const pending = { source: 'pending', build: 'pending', probe: 'pending', realDevice: 'pending' };
  assert.deepEqual(matrix.coverage, pending);
  assert.deepEqual(matrix.environmentTemplate.coverage, pending);
  for (const evidence of Object.values(matrix.environmentTemplate.evidence)) assert.deepEqual(evidence, []);
});

test('synthetic only: initial load and refresh do not download or invoke network/private APIs', () => {
  const probe = boot({ hints: true });
  probe.elements.refresh.click();
  assert.equal(probe.calls.blobs.length, 0);
  assert.equal(probe.calls.downloads.length, 0);
  assert.deepEqual(probe.calls.forbidden, []);
  assert.match(html, /connect-src 'none'/);
  assert.doesNotMatch(html, /<(?:script|img|iframe|link)\b[^>]*(?:src|href)\s*=\s*["'][^#]/i);
  assert.doesNotMatch(source, /\?\.|\b(?:const|let|async|await|Promise)\b|=>|innerHTML|new\s+Function|\beval\s*\(/);
});

test('synthetic only: explicit export preserves metadata and unverified manual input without reading IME/storage', () => {
  const probe = boot({ hints: true });
  const unsafeLookingText = '<img src=x onerror=alert(1)>';
  probe.elements['os-version'].value = '  synthetic OS  ';
  probe.elements.architecture.value = '   ';
  probe.elements['browser-version'].value = unsafeLookingText;
  probe.elements['kernel-version'].value = ' Chromium synthetic ';
  probe.elements['review-colors'].value = 'fail';
  probe.elements['review-ime'].value = 'pass';
  probe.elements.theme.click();
  const report = probe.exportReport();
  assert.equal(report.schemaVersion, 1);
  assert.ok(Number.isFinite(Date.parse(report.timestamp)));
  assert.equal(report.ua, 'synthetic-test-not-device-evidence');
  assert.equal(report.platform, 'synthetic-platform');
  assert.equal(report.language, 'zh-CN');
  assert.equal(report.dpr, 1.25);
  assert.deepEqual(report.viewport, { width: 1024, height: 768 });
  assert.equal(report.secureContext, false);
  assert.ok(report.features.length > 0);
  assert.deepEqual(report.manualEnvironment, {
    verification: 'unverified-user-input', osVersion: 'synthetic OS',
    architecture: 'unknown', browserFullVersion: unsafeLookingText,
    browserKernelVersion: 'Chromium synthetic'
  });
  assert.equal(report.manualObservations.source, 'manual-user-selection-not-automatically-verified');
  assert.equal(report.manualObservations.colors, 'fail');
  assert.equal(report.manualObservations.fontAndIme, 'pass');
  assert.equal(report.manualObservations.webglRealDeviceVisual, 'unknown');
  assert.equal(report.presentation.manualDark, true);
  assert.equal(report.clientHints.available, true);
  assert.deepEqual(report.clientHints.brands, [{ brand: 'Synthetic', version: '0' }]);
  assert.equal(report.clientHints.mobile, false);
  assert.equal(report.clientHints.platform, 'synthetic-hints-platform');
  assert.equal(probe.calls.downloads.length, 1);
  assert.match(probe.calls.downloads[0].filename, /^browser-probe-.*\.json$/);
  assert.equal(probe.calls.blobs[0].type, 'application/json;charset=utf-8');
  assert.deepEqual(probe.calls.forbidden, []);
  assert.equal(probe.document.body.children.length, 0, 'temporary anchor removed');
  for (const timer of probe.calls.timers) timer();
  assert.deepEqual(probe.calls.revoked, ['blob:synthetic-probe-download']);
});

test('synthetic only: absent CSS.supports remains unknown, never inferred as rendering success', () => {
  const probe = boot();
  const report = probe.exportReport();
  const syntax = report.features.filter(feature => feature.kind === 'css-syntax-only');
  assert.ok(syntax.length > 0);
  for (const feature of syntax) assert.equal(feature.result, 'unknown');
  assert.equal(report.clientHints.available, false);
  assert.match(report.computedColors.note, /不能验证截图/);
  assert.deepEqual(probe.calls.forbidden, []);
});

test('synthetic only: CSS syntax false and exceptions are not promoted to support', () => {
  const css = { supports(property) {
    if (property === 'color') throw new Error('synthetic CSS failure');
    return false;
  } };
  const probe = boot({ css });
  const syntax = probe.exportReport().features.filter(feature => feature.kind === 'css-syntax-only');
  assert.equal(syntax.find(feature => feature.name === 'lab()').result, 'unknown');
  assert.equal(syntax.find(feature => feature.name === 'Grid').result, false);
  assert.equal(syntax.find(feature => feature.name === ':focus-visible').result, false);
});

test('synthetic only: viewport, container and has probes use the correct CSS.supports overloads', () => {
  const seen = [];
  const probe = boot({ css: { supports(...args) { seen.push(args); return true; } } });
  const syntax = probe.exportReport().features.filter(feature => feature.kind === 'css-syntax-only');
  for (const value of ['20svh', '20lvh']) {
    assert.ok(seen.some(args => args.length === 2 && args[0] === 'height' && args[1] === value));
  }
  assert.ok(seen.some(args => args.length === 2 && args[0] === 'container-type' && args[1] === 'inline-size'));
  assert.ok(seen.some(args => args.length === 1 && args[0] === 'selector(:has(*))'));
  assert.equal(syntax.find(feature => feature.name === ':has()').result, true);
  assert.match(syntax.find(feature => feature.property === 'container-type').name, /不代表全部容器查询/);
});

test('synthetic only: svh/lvh/container syntax and :has use their expected CSS.supports overloads', () => {
  const calls = [];
  const probe = boot({ css: { supports(...args) { calls.push(args); return true; } } });
  const report = probe.exportReport();
  for (const value of ['20svh', '20lvh']) {
    assert.ok(calls.some(args => args.length === 2 && args[0] === 'height' && args[1] === value));
    assert.equal(report.features.find(feature => feature.property === 'height' && feature.value === value).result, true);
  }
  const container = report.features.find(feature => feature.property === 'container-type');
  assert.equal(container.value, 'inline-size');
  assert.equal(container.result, true);
  assert.match(container.note, /仅.*属性语法/);
  assert.match(container.note, /不等同全部 @container 查询/);
  assert.ok(calls.some(args => args.length === 2 && args[0] === 'container-type' && args[1] === 'inline-size'));
  const hasCalls = calls.filter(args => args[0] === 'selector(:has(*))');
  assert.ok(hasCalls.length > 0);
  assert.ok(hasCalls.every(args => args.length === 1), ':has selector requires single-argument overload');
  assert.equal(report.features.find(feature => feature.property === 'selector(:has(*))').result, true);
  assert.deepEqual(probe.calls.forbidden, []);
});

test('synthetic only: newly required CSS probes remain unknown when API is missing or throws', () => {
  const variants = [{}, { css: {} }, { css: { supports() { throw new Error('synthetic unsupported API'); } } }];
  for (const options of variants) {
    const probe = boot(options);
    const features = probe.exportReport().features;
    for (const value of ['20svh', '20lvh']) {
      assert.equal(features.find(feature => feature.property === 'height' && feature.value === value).result, 'unknown');
    }
    assert.equal(features.find(feature => feature.property === 'container-type').result, 'unknown');
    assert.equal(features.find(feature => feature.property === 'selector(:has(*))').result, 'unknown');
    assert.deepEqual(probe.calls.forbidden, []);
  }
});

test('synthetic only: missing Blob never falls back to network upload', () => {
  const probe = boot({ noBlob: true });
  probe.elements.export.click();
  assert.equal(probe.calls.blobs.length, 0);
  assert.equal(probe.calls.downloads.length, 0);
  assert.match(probe.elements['export-status'].textContent, /缺少 Blob/);
  assert.deepEqual(probe.calls.forbidden, []);
});

test('synthetic only: modal traps Tab, closes with Escape and restores opener focus', () => {
  const probe = boot();
  const elements = probe.elements;
  const opener = elements['open-dialog'];
  opener.focus();
  opener.click();
  assert.equal(elements.overlay.style.display, 'block');
  assert.equal(elements.overlay.attributes['aria-hidden'], 'false');
  assert.equal(probe.document.activeElement, elements['dialog-confirm']);
  assert.equal(probe.key(9, true), true);
  assert.equal(probe.document.activeElement, elements['dialog-close']);
  assert.equal(probe.key(9), true);
  assert.equal(probe.document.activeElement, elements['dialog-confirm']);
  elements.refresh.focus();
  assert.equal(probe.document.activeElement, elements['dialog-confirm'], 'outside focus is returned inside');
  assert.equal(probe.key(27), true);
  assert.equal(elements.overlay.style.display, 'none');
  assert.equal(elements.overlay.attributes['aria-hidden'], 'true');
  assert.equal(probe.document.activeElement, opener);
  opener.click();
  elements['dialog-close'].click();
  assert.equal(probe.document.activeElement, opener);
  opener.click();
  elements['dialog-confirm'].click();
  assert.equal(probe.document.activeElement, opener);
  assert.deepEqual(probe.calls.forbidden, []);
});

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {htmlPathToRoute, loadPublicationRoutes, priorityRoutes, routesFromManifest} = require('../scripts/publication_routes.cjs');

test('HTML paths map to their public routes', () => {
  assert.equal(htmlPathToRoute('index.html'), '/');
  assert.equal(htmlPathToRoute('guias/index.html'), '/guias/');
  assert.equal(htmlPathToRoute('guia/exemplo.html'), '/guia/exemplo.html');
  const backslashPath = 'guia' + String.fromCharCode(92) + 'item.html';
  for (const unsafe of ['../index.html', '/index.html', 'index.htm', backslashPath, 'guia/a.html?x=1'])
    assert.throws(() => htmlPathToRoute(unsafe), /UNSAFE_PUBLIC_HTML_PATH/);
});

test('capture route set equals the reviewed publication manifest', () => {
  const root = path.resolve(__dirname, '..');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'data/publication-manifest.json'), 'utf8'));
  const routes = loadPublicationRoutes(root);
  assert.equal(routes.length, manifest.html.length);
  assert.equal(new Set(routes).size, routes.length);
  assert.deepEqual(new Set(routes), new Set(manifest.html.map(htmlPathToRoute)));
  assert.deepEqual(routes.slice(0, priorityRoutes.length), priorityRoutes);
});

test('manifest loader rejects duplicate and unsafe publication entries', () => {
  assert.throws(() => routesFromManifest({version:1, html:['index.html','index.html']}), /DUPLICATE_PUBLIC_ROUTE/);
  assert.throws(() => routesFromManifest({version:1, html:['../outside.html']}), /UNSAFE_PUBLIC_HTML_PATH/);
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cortex-routes-'));
  try {
    fs.mkdirSync(path.join(root, 'data'));
    fs.writeFileSync(path.join(root, 'data', 'publication-manifest.json'), '{"version":1,"html":[]}');
    assert.throws(() => loadPublicationRoutes(root), /INVALID_PUBLICATION_MANIFEST/);
  } finally {
    fs.rmSync(root, {recursive:true, force:true});
  }
});

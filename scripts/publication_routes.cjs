'use strict';

const fs = require('node:fs');
const path = require('node:path');

const priorityRoutes = [
  '/', '/setup-games/', '/trabalho-estudo/', '/creator-streaming/',
  '/casa-inteligente/', '/guias/', '/comparativos/', '/recomendados/',
  '/guia/melhor-webcam-para-stream.html',
  '/guia/melhor-headset-gamer-custo-beneficio.html',
  '/guia/setup-gamer-custo-beneficio.html',
  '/guia/havit-h2002d-quando-faz-sentido.html',
  '/guia/smart-plug-max-quando-faz-sentido.html',
  '/politica-de-privacidade.html'
];

function htmlPathToRoute(relativePath) {
  if (typeof relativePath !== 'string' || !relativePath.endsWith('.html') ||
      relativePath.includes('\\') || relativePath.includes('?') || relativePath.includes('#') ||
      path.posix.isAbsolute(relativePath)) {
    throw new Error(`UNSAFE_PUBLIC_HTML_PATH: ${relativePath}`);
  }
  const normalized = path.posix.normalize(relativePath);
  if (normalized !== relativePath || normalized === '..' || normalized.startsWith('../')) {
    throw new Error(`UNSAFE_PUBLIC_HTML_PATH: ${relativePath}`);
  }
  if (normalized === 'index.html') return '/';
  if (normalized.endsWith('/index.html')) return `/${normalized.slice(0, -'index.html'.length)}`;
  return `/${normalized}`;
}

function routesFromManifest(manifest) {
  if (!manifest || manifest.version !== 1 || !Array.isArray(manifest.html) || !manifest.html.length) {
    throw new Error('INVALID_PUBLICATION_MANIFEST');
  }
  const routes = manifest.html.map(htmlPathToRoute);
  if (new Set(routes).size !== routes.length) throw new Error('DUPLICATE_PUBLIC_ROUTE');
  const rank = new Map(priorityRoutes.map((route, index) => [route, index]));
  return routes.sort((a, b) => {
    const ar = rank.has(a) ? rank.get(a) : Number.MAX_SAFE_INTEGER;
    const br = rank.has(b) ? rank.get(b) : Number.MAX_SAFE_INTEGER;
    return ar - br || a.localeCompare(b, 'pt-BR');
  });
}

function loadPublicationRoutes(root = path.resolve(__dirname, '..')) {
  const manifestPath = path.join(root, 'data', 'publication-manifest.json');
  return routesFromManifest(JSON.parse(fs.readFileSync(manifestPath, 'utf8')));
}

module.exports = {htmlPathToRoute, loadPublicationRoutes, priorityRoutes, routesFromManifest};

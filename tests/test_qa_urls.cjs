const test = require('node:test');
const assert = require('node:assert/strict');
const {canonicalMatches, internalPath} = require('../scripts/qa_urls.cjs');
const base = 'https://cortex-ofertas.pages.dev';
test('canonical requires one exact origin and matching route', () => {
  for (const path of ['/guias/', '/guias/index.html'])
    assert.equal(canonicalMatches([base + path], base, '/guias/'), true);
  for (const values of [[], [base, base], [base + '.evil.test/guias/'],
    [base + '/wrong/'], [base + '/guias/?x=1'], [base + '/guias/#x'],
    ['/guias/'], ['https://user@cortex-ofertas.pages.dev/guias/']])
    assert.equal(canonicalMatches(values, base, '/guias/'), false);
});
test('relative and absolute internal links preserve route and query', () => {
  const preview = 'https://candidate.cortex-ofertas.pages.dev';
  for (const [href, expected] of [['../guia/a.html#specs', '/guia/a.html'],
    ['detail.html?variant=2', '/guias/detail.html?variant=2'],
    [base + '/setup-games/', '/setup-games/'],
    [preview + '/guias/', '/guias/'],
    ['//cortex-ofertas.pages.dev/guias/', '/guias/'],
    [base + '.evil.test/', null], ['mailto:test@example.com', null]])
    assert.equal(internalPath(href, preview + '/guias/', [base, preview]), expected);
  assert.throws(() => internalPath('http://[invalid', preview, [base, preview]));
});

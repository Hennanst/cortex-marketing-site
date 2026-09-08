'use strict';
// Shared by live QA and offline regressions; these functions perform no I/O.
function canonicalMatches(values, productionBase, route) {
  if (values.length !== 1) return false;
  try {
    const actual = new URL(values[0]);
    const expected = new URL(route, productionBase);
    return actual.origin === expected.origin && !actual.username && !actual.password &&
      !actual.search && !actual.hash &&
      (actual.pathname === expected.pathname ||
       (expected.pathname.endsWith('/') && actual.pathname === expected.pathname + 'index.html'));
  } catch { return false; }
}
function internalPath(href, pageUrl, allowedBases) {
  const url = new URL(href, pageUrl);
  if (!['http:', 'https:'].includes(url.protocol)) return null;
  if (!allowedBases.some(base => new URL(base).origin === url.origin)) return null;
  if (url.username || url.password) throw new Error('Internal URL contains credentials');
  return url.pathname + url.search;
}
module.exports = {canonicalMatches, internalPath};

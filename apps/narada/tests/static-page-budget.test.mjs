import assert from 'node:assert/strict';
import test from 'node:test';
import { assertPagePayloadSize, HTML_PAGE_MAX_BYTES, RSC_PAGE_MAX_BYTES } from '../scripts/lib/static-page-budget.mjs';

test('rendered HTML and serialized React payloads accept their exact bounds and refuse one byte above', () => {
  assert.equal(HTML_PAGE_MAX_BYTES, 768 * 1024);
  assert.equal(RSC_PAGE_MAX_BYTES, 512 * 1024);
  for (const [file, budget] of [['index.html', HTML_PAGE_MAX_BYTES], ['index.txt', RSC_PAGE_MAX_BYTES], ['page.rsc', RSC_PAGE_MAX_BYTES]]) {
    assert.equal(assertPagePayloadSize(file, budget), true);
    assert.throws(() => assertPagePayloadSize(file, budget + 1), /exceeds its static page budget/);
  }
});

test('dense saved-table rendering fits while invalid byte counts and unsupported types remain separate', () => {
  assert.equal(assertPagePayloadSize('study/index.html', 642042), true);
  assert.equal(assertPagePayloadSize('study/__next._full.txt', 378096), true);
  for (const bytes of [-1, NaN, Infinity, .5, '100']) {
    assert.throws(() => assertPagePayloadSize('index.html', bytes), /byte count/);
  }
  for (const file of ['report.json', 'selected.csv', 'chart.png', 'script.js']) {
    assert.equal(assertPagePayloadSize(file, 1024 * 1024), false, 'Publication and asset validators retain their own budgets.');
  }
});

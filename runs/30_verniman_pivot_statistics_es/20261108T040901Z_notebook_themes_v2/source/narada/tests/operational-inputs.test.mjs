import assert from 'node:assert/strict';
import test from 'node:test';
import { validateCsv, validateReferenceUrl } from '../scripts/lib/evidence.mjs';
import { validateStudyCatalog } from '../scripts/lib/studies.mjs';

// Character-code checks replace lint-rejected control-character regexes while
// retaining the three established input policies, including their whitespace.
test('reference URLs reject ASCII controls, whitespace and backslashes', () => {
  for (const code of [...Array(32).keys(), 32, 127]) {
    assert.throws(() => validateReferenceUrl(`https://example.org/a${String.fromCharCode(code)}b`), /clean HTTPS/);
  }
  assert.throws(() => validateReferenceUrl('https://example.org/a\\b'), /clean HTTPS/);
  assert.equal(validateReferenceUrl('https://example.org/a-b?time=0'), 'https://example.org/a-b?time=0');
});

test('CSV retains tab, LF and CR but rejects its established forbidden controls', () => {
  const declaration = { columns: ['value'], rowCount: 1 };
  for (const code of [...Array(32).keys(), 127]) {
    const value = `a${String.fromCharCode(code)}b`;
    const bytes = Buffer.from(`value\n"${value}"\n`);
    if ([9, 10, 13].includes(code)) {
      assert.deepEqual(validateCsv(bytes, declaration), [['value'], [value]]);
    } else {
      assert.throws(() => validateCsv(bytes, declaration), /forbidden control/);
    }
  }
});

test('catalog text retains internal tab and LF while rejecting CR and other ASCII controls', () => {
  const reports = [{ id: 'selected', source: { producer: 'sahadeva', runId: 'run_a' } }];
  const catalog = summary => ({ schemaVersion: '1.0', studies: [{ studyId: '01_test', slug: 'test',
    title: 'Synthetic test', summary, topic: 'Testing', products: ['NQ'], evidenceStatus: 'Synthetic only',
    featuredPublicationId: 'selected', featuredSourceRunId: 'run_a' }] });
  for (const code of [...Array(32).keys(), 127]) {
    const value = catalog(`a${String.fromCharCode(code)}b`);
    if ([9, 10].includes(code)) {
      assert.equal(validateStudyCatalog(value, reports), value);
    } else {
      assert.throws(() => validateStudyCatalog(value, reports), /control characters/);
    }
  }
});

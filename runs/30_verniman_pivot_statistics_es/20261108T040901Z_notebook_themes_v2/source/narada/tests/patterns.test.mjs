import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { validateReport } from '../scripts/lib/publication.mjs';

const example = JSON.parse(await readFile(new URL('../examples/report.json', import.meta.url), 'utf8'));
function report() {
  const result = structuredClone(example);
  result.schemaVersion = '1.1';
  result.patterns = [{ id: 'setup', title: 'Illustrative setup', description: 'A schematic with normalized prices.', variants: [{ id: 'bullish', title: 'Bullish', description: 'Signal and next candle.', candles: [
    { id: 'r', label: 'R', open: 40, high: 80, low: 35, close: 70, role: 'signal' },
    { id: 'f1', label: 'F1', open: 70, high: 95, low: 55, close: 90, role: 'measured' },
  ], marks: [{ kind: 'span', startCandle: 'r', endCandle: 'f1', label: 'Signal then next candle' }, { kind: 'level', startCandle: 'r', endCandle: 'f1', price: 70, label: 'Signal close' }, { kind: 'band', startCandle: 'r', endCandle: 'f1', low: 40, high: 70, label: 'Signal body' }] }] }];
  result.patternOverviewId = 'setup';
  result.sections[2].patternId = 'setup';
  result.sections[2].patternFocus = 'The next candle is measured.';
  return result;
}
test('patterns are explicit saved presentation geometry; validation leaves scalar results unchanged', () => {
  const source = report();
  const before = structuredClone(source);
  assert.equal(validateReport(source), source);
  assert.deepEqual(source, before);
  assert.deepEqual(source.sections[2].rows, example.sections[2].rows);
  assert.deepEqual(validateReport(structuredClone(example)), example);
});
test('pattern and variant references fail closed for missing, duplicated and reversed identities', () => {
  for (const change of [
    r => r.patterns.push(structuredClone(r.patterns[0])),
    r => r.patterns[0].variants.push(structuredClone(r.patterns[0].variants[0])),
    r => r.patterns[0].variants[0].candles[1].id = 'r',
    r => r.patternOverviewId = 'missing',
    r => r.sections[2].patternId = 'missing',
    r => delete r.sections[2].patternId,
    r => r.patterns[0].variants[0].marks[0].startCandle = 'missing',
    r => { r.patterns[0].variants[0].marks[0].startCandle = 'f1'; r.patterns[0].variants[0].marks[0].endCandle = 'r'; },
  ]) {
    const source = report(); change(source); assert.throws(() => validateReport(source));
  }
});
test('geometry is bounded and OHLC ordered without admitting raw SVG or arbitrary drawing content', () => {
  for (const change of [
    r => r.patterns[0].variants[0].candles[0].open = 81,
    r => r.patterns[0].variants[0].candles[0].close = 34,
    r => r.patterns[0].variants[0].candles[0].low = -1,
    r => r.patterns[0].variants[0].candles[0].high = 101,
    r => r.patterns[0].variants[0].candles[0].role = 'winning-trade',
    r => r.patterns[0].variants[0].marks[1].price = 101,
    r => r.patterns[0].variants[0].marks[2].low = 70,
    r => r.patterns[0].svg = '<svg onload="unsafe"/>',
    r => r.patterns[0].variants[0].marks[0].html = 'unsafe',
    r => r.patterns[0].variants[0].marks[0].price = 60,
    r => r.patterns[0].variants[0].marks[1].low = 0,
  ]) {
    const source = report(); change(source); assert.throws(() => validateReport(source));
  }
});
test('patterns keep fixed item and text budgets and remain opt-in only on version 1.1', () => {
  for (const change of [
    r => r.schemaVersion = '1.0',
    r => r.patterns = Array.from({ length: 13 }, (_, i) => ({ ...r.patterns[0], id: `pattern-${i}` })),
    r => r.patterns[0].variants = Array.from({ length: 3 }, (_, i) => ({ ...r.patterns[0].variants[0], id: `variant-${i}` })),
    r => r.patterns[0].variants[0].candles = Array.from({ length: 13 }, (_, i) => ({ ...r.patterns[0].variants[0].candles[0], id: `candle-${i}` })),
    r => r.patterns[0].variants[0].marks = Array.from({ length: 9 }, () => r.patterns[0].variants[0].marks[0]),
    r => r.sections[2].patternFocus = 'x'.repeat(501),
    r => r.patterns[0].variants[0].candles[0].label = 'x'.repeat(21),
  ]) {
    const source = report(); change(source); assert.throws(() => validateReport(source));
  }
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { formatValue, formatDate } from '../src/lib/format.ts';

test('explicit formats preserve scale, zero, missing values, and units', () => {
  assert.equal(formatValue(0.25, { format: 'percent', precision: 1 }), '25.0%');
  assert.equal(formatValue(0.25, { format: 'number', precision: 2, unit: 'units' }), '0.25 units');
  assert.equal(formatValue(0, { format: 'number', precision: 0 }), '0');
  assert.equal(formatValue(null), 'Not available');
  assert.equal(formatValue(false), 'false');
  assert.equal(formatValue(-2.125, { precision: 3, unit: 'ms' }), '-2.125 ms');
});

test('publication dates use UTC regardless of the reader time zone', () => {
  assert.equal(formatDate('2026-01-01T00:00:00Z'), 'January 1, 2026');
});

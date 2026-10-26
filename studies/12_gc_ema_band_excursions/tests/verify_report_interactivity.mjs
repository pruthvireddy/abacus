// Exercise the report's embedded script with a minimal DOM stand-in.
// This catches runtime errors that a syntax-only check misses.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const path = process.argv[2];
if (!path) throw new Error('usage: node verify_report_interactivity.mjs <report.html>');
const html = readFileSync(path, 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'embedded script exists');
const fallback = html.match(/<tbody id="year-rows">([\s\S]*?)<\/tbody>/)?.[1];
assert.ok(fallback, 'default table is pre-rendered');
assert.equal((fallback.match(/<tr>/g) || []).length, 17);

const ids = ['cooldown', 'horizon', 'card-n', 'card-mae', 'card-mfe',
  'card-positive', 'year-rows', 'bars'];
const nodes = new Map(ids.map(id => [id, {
  value: id === 'cooldown' ? '10' : id === 'horizon' ? '20' : '',
  textContent: '', innerHTML: '', handlers: {},
  addEventListener(type, handler) { this.handlers[type] = handler; },
}]));
const context = { document: { getElementById(id) {
  const node = nodes.get(id);
  assert.ok(node, `known DOM id: ${id}`);
  return node;
} } };
vm.runInNewContext(script, context, { timeout: 5000 });

const initial = nodes.get('year-rows').innerHTML;
assert.equal((initial.match(/<tr>/g) || []).length, 17);
assert.match(initial, /2026 YTD/);
assert.match(initial, /245/);
assert.match(nodes.get('card-n').textContent, /^[0-9,]+$/);
assert.match(nodes.get('card-positive').textContent, /%$/);

nodes.get('cooldown').value = '30';
nodes.get('horizon').value = '100';
nodes.get('cooldown').handlers.change();
const changed = nodes.get('year-rows').innerHTML;
assert.equal((changed.match(/<tr>/g) || []).length, 17);
assert.notEqual(changed, initial, 'selectors update the saved result table');
assert.match(nodes.get('bars').innerHTML, /bar-mfe/);
for (const cooldown of [0, 5, 10, 20, 30]) {
  for (const horizon of [5, 10, 15, 20, 30, 50, 100]) {
    nodes.get('cooldown').value = String(cooldown);
    nodes.get('horizon').value = String(horizon);
    nodes.get('horizon').handlers.change();
    assert.equal((nodes.get('year-rows').innerHTML.match(/<tr>/g) || []).length, 17);
    assert.match(nodes.get('card-n').textContent, /^[0-9,]+$/);
  }
}
console.log('report script rendered all 35 selector combinations; default table works without script');

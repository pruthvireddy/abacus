import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import ts from 'typescript';

function loader() {
  const source = readFileSync(new URL('../src/lib/saved-tables.ts', import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } });
  const compiledModule = { exports: {} }; new Function('module', 'exports', outputText)(compiledModule, compiledModule.exports); return compiledModule.exports.loadSavedTables;
}
const body = id => ({ report: { id, sections: [{ id: 'saved', kind: 'table', rows: [{ value: 0 }] }, { id: 'meaning', kind: 'text', body: 'Saved prose' }] } });

test('saved table controls share one immutable JSON fetch and retain exact saved rows', async t => {
  const prior = globalThis.fetch; t.after(() => { globalThis.fetch = prior; }); let calls = 0;
  globalThis.fetch = async url => { calls++; assert.equal(url, '/publications/saved-report/report.json'); return new Response(JSON.stringify(body('saved-report')), { headers: { 'content-type': 'application/json' } }); };
  const load = loader(); const [first, second] = await Promise.all([load('saved-report'), load('saved-report')]);
  assert.equal(calls, 1); assert.equal(first, second); assert.deepEqual(first[0].rows, [{ value: 0 }]); assert.equal(first.length, 1);
});
test('failed saved-table loads can retry while changed identities, errors and oversized bytes fail closed', async t => {
  const prior = globalThis.fetch; t.after(() => { globalThis.fetch = prior; }); const load = loader(); let calls = 0;
  globalThis.fetch = async () => { calls++; return new Response(JSON.stringify(body('saved-report')), { status: calls === 1 ? 404 : 200 }); };
  await assert.rejects(load('saved-report'), /unavailable/); assert.equal((await load('saved-report')).length, 1); assert.equal(calls, 2);
  globalThis.fetch = async () => new Response(JSON.stringify(body('different'))); await assert.rejects(loader()('saved-report'), /identity changed/);
  globalThis.fetch = async () => new Response('{}', { headers: { 'content-length': String(4 * 1024 * 1024 + 1) } }); await assert.rejects(loader()('saved-report'), /byte bound/);
  globalThis.fetch = async () => new Response(' '.repeat(4 * 1024 * 1024 + 1)); await assert.rejects(loader()('saved-report'), /byte bound/);
  await assert.rejects(loader()('../private'), /Invalid saved publication identity/);
});

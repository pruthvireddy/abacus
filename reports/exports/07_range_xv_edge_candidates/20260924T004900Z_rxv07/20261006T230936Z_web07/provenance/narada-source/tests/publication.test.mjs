import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, mkdir, rm, symlink, readdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { validateReport, publishReport, verifyPublications } from '../scripts/lib/publication.mjs';
const example=JSON.parse(await readFile(new URL('../examples/report.json',import.meta.url),'utf8'));
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOioAAAAASUVORK5CYII=','base64');
async function fixture(t,{figure=false}={}) {
  const root=await mkdtemp(resolve(tmpdir(),'narada-test-')); t.after(()=>rm(root,{recursive:true,force:true}));
  const source=resolve(root,'source');await mkdir(source); const report=structuredClone(example);
  if(figure) {await mkdir(resolve(source,'figures'));await writeFile(resolve(source,'figures/example.png'),png);report.sections.push({id:'figure',kind:'figure',title:'Illustrative pixel',path:'figures/example.png',alt:'A one-pixel fixture for publication verification'});}
  const reportPath=resolve(source,'report.json');await writeFile(reportPath,JSON.stringify(report));
  return {root,source,report,reportPath,outputRoot:resolve(root,'publications')};
}
test('strict contract rejects unknown containers, duplicate sections, undeclared row keys and invalid dates',()=>{
  for(const change of [r=>r.secret={bars:[]},r=>r.sections.push(r.sections[0]),r=>r.sections[2].rows[0].unlisted='x',r=>r.publishedAt='2026-02-30T00:00:00Z',r=>r.sections[1].items[0].precision=7,r=>r.sections[2].rows[0].value='not numeric']) {const report=structuredClone(example);change(report);assert.throws(()=>validateReport(report));}
});
test('dry run writes nothing and ordinary publication verifies',async t=>{
  const f=await fixture(t);const result=await publishReport({...f,dryRun:true});assert.equal(result.status,'ready');assert.deepEqual(await readdir(f.root),['source']);
  assert.equal((await publishReport(f)).status,'published');assert.equal((await verifyPublications(f.outputRoot)).reports,1);
});
test('deterministic output and formatting-only idempotence',async t=>{
  const f=await fixture(t,{figure:true});await publishReport(f);const bundlePath=resolve(f.outputRoot,f.report.id,'report.json');const before=await readFile(bundlePath,'utf8');
  await writeFile(f.reportPath,JSON.stringify(f.report,null,4)+'\n');assert.equal((await publishReport(f)).status,'unchanged');assert.equal(await readFile(bundlePath,'utf8'),before);
  const second=resolve(f.root,'second');await publishReport({...f,outputRoot:second});assert.equal(await readFile(resolve(second,f.report.id,'report.json'),'utf8'),before);
  assert.equal((await verifyPublications(f.outputRoot)).assets,1);
});
test('changed existing ID is rejected without damaging the published result',async t=>{
  const f=await fixture(t);await publishReport(f);f.report.summary='A changed illustrative summary';await writeFile(f.reportPath,JSON.stringify(f.report));
  await assert.rejects(publishReport(f),/new report ID/);assert.equal((await verifyPublications(f.outputRoot)).reports,1);assert(!(await readdir(f.root)).some(n=>n.startsWith('.')));
});
test('path traversal, symlink escape, and false raster signatures are rejected',async t=>{
  const f=await fixture(t,{figure:true});const figure=f.report.sections.at(-1);figure.path='../outside.png';await writeFile(f.reportPath,JSON.stringify(f.report));await assert.rejects(publishReport(f),/schema/);
  figure.path='figures/example.png';await writeFile(f.reportPath,JSON.stringify(f.report));await rm(resolve(f.source,figure.path));await writeFile(resolve(f.root,'outside.png'),png);await symlink(resolve(f.root,'outside.png'),resolve(f.source,figure.path));await assert.rejects(publishReport(f),/symlink/);
  await rm(resolve(f.source,figure.path));await writeFile(resolve(f.source,figure.path),'not an image');await assert.rejects(publishReport(f),/signature/);
});
test('modified assets, report content, stale files, and index drift fail verification',async t=>{
  const f=await fixture(t,{figure:true});await publishReport(f);const dir=resolve(f.outputRoot,f.report.id);const asset=resolve(dir,'figures/example.png');
  const altered=Buffer.from(png);altered[altered.length-1]^=1;await writeFile(asset,altered);await assert.rejects(verifyPublications(f.outputRoot),/Modified asset/);await writeFile(asset,png);
  const file=resolve(dir,'report.json');const original=await readFile(file,'utf8');const bundle=JSON.parse(original);bundle.report.sections[0].body='Changed';await writeFile(file,JSON.stringify(bundle));await assert.rejects(verifyPublications(f.outputRoot),/source hash/);await writeFile(file,original);
  const stale=resolve(dir,'extra.json');await writeFile(stale,'{}');await assert.rejects(verifyPublications(f.outputRoot),/stale or unselected/);await rm(stale);
  const indexPath=resolve(f.outputRoot,'index.json');const index=JSON.parse(await readFile(indexPath));index.reports[0].summary='stale';await writeFile(indexPath,JSON.stringify(index));await assert.rejects(verifyPublications(f.outputRoot),/index is stale/);
});
test('report and asset budgets reject oversized inputs',async t=>{
  const f=await fixture(t,{figure:true});await writeFile(resolve(f.source,'figures/example.png'),Buffer.alloc(2*1024*1024+1));await assert.rejects(publishReport(f),/budget/);
  await writeFile(f.reportPath,' '.repeat(96*1024+1));await assert.rejects(publishReport(f),/budget/);
});
test('concurrent publication lock is respected and unrelated files are never copied',async t=>{
  const f=await fixture(t);await writeFile(resolve(f.source,'private.txt'),'not for publication');await writeFile(resolve(f.root,'.publications.publish.lock'),'');await assert.rejects(publishReport(f),/in progress/);
  await rm(resolve(f.root,'.publications.publish.lock'));await publishReport(f);assert.deepEqual(await readdir(resolve(f.outputRoot,f.report.id)),['report.json']);
});
test('missing selected figure leaves existing publication bytes and index unchanged',async t=>{
  const f=await fixture(t);await publishReport(f);const indexPath=resolve(f.outputRoot,'index.json');const before=await readFile(indexPath,'utf8');const reportPath=resolve(f.outputRoot,f.report.id,'report.json');const reportBefore=await readFile(reportPath,'utf8');
  f.report.id='second-illustrative-report';f.report.sections.push({id:'missing',kind:'figure',title:'Missing figure',path:'figures/missing.png',alt:'Missing illustrative figure'});await writeFile(f.reportPath,JSON.stringify(f.report));
  await assert.rejects(publishReport(f),/ENOENT/);assert.equal(await readFile(indexPath,'utf8'),before);assert.equal(await readFile(reportPath,'utf8'),reportBefore);assert.deepEqual((await readdir(f.outputRoot)).sort(),['illustrative-report','index.json']);assert(!(await readdir(f.root)).some(n=>n.startsWith('.')));
});
test('an empty symlink output directory is rejected',async t=>{
  const f=await fixture(t);const target=resolve(f.root,'target');await mkdir(target);await symlink(target,f.outputRoot);await assert.rejects(publishReport(f),/real directory/);assert.deepEqual(await readdir(target),[]);
});
test('index orders timestamps chronologically across optional milliseconds',async t=>{
  const f=await fixture(t);await publishReport(f);f.report.id='later-report';f.report.publishedAt='2026-01-01T00:00:00.100Z';await writeFile(f.reportPath,JSON.stringify(f.report));await publishReport(f);const index=JSON.parse(await readFile(resolve(f.outputRoot,'index.json')));assert.deepEqual(index.reports.map(r=>r.id),['later-report','illustrative-report']);await verifyPublications(f.outputRoot);
});

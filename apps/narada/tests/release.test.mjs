import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, mkdir, symlink, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';
import { hash, inventory, inventoryHash, verifyInventory, copyInventory, validateStaticFiles, buildOutputConfig, deployArgs, deploymentResult, run, checkHosted, safeId, parseHttpResponse } from '../scripts/lib/release.mjs';
const catalog={studies:[{slug:'one'}]},bundles=[{report:{id:'real',downloads:[{path:'downloads/summary.csv'}]},provenance:{assets:[{path:'downloads/summary.csv'}]}}];
const names=['index.html','404.html','404/index.html','_not-found/index.html',...['', 'findings/', 'explore/', 'methods/', 'evidence/'].map(path=>`studies/one/${path}index.html`),'reports/real/index.html','publications/index.json','publications/real/report.json','publications/real/downloads/summary.csv'];
async function fixture(t) {
  const root=await mkdtemp(resolve(tmpdir(),'narada-release-'));t.after(()=>rm(root,{recursive:true,force:true}));
  for(const file of names){await mkdir(resolve(root,file,'..'),{recursive:true});await writeFile(resolve(root,file),file);}
  return root;
}
test('release boundary admits selected pages/assets and rejects private or unknown output',async t=>{
  const root=await fixture(t),files=await inventory(root);validateStaticFiles(files,catalog,bundles);
  for(const path of ['source-map.json','studies/unselected/index.html','publications/real/manifest.json','_next/static/private.env','reports/real/captions.txt'])
    assert.throws(()=>validateStaticFiles([...files,{path}],catalog,bundles),/Unselected/);
  assert.throws(()=>validateStaticFiles(files.filter(f=>f.path!=='reports/real/index.html'),catalog,bundles),/Missing/);
});
test('exact inventory copy rejects symlinks, additions and modified bytes',async t=>{
  const root=await fixture(t),files=await inventory(root),target=resolve(root,'../copy-'+crypto.randomUUID());t.after(()=>rm(target,{recursive:true,force:true}));
  await copyInventory(root,target,files);assert.equal(inventoryHash(await inventory(target)),inventoryHash(files));
  await writeFile(resolve(target,'index.html'),'changed');await assert.rejects(verifyInventory(target,files),/inventory changed/);
  await symlink(resolve(root,'index.html'),resolve(root,'private-link'));await assert.rejects(inventory(root),/Symlinks/);
});
test('deployment format has explicit routes, attachment headers and a hard 404',()=>{
  const config=buildOutputConfig(catalog,bundles);assert.equal(config.version,3);
  assert(config.routes.some(r=>r.dest==='/studies/one/index.html'));
  assert.equal(config.routes[0].headers['Content-Disposition'],'attachment; filename="summary.csv"');
  assert.deepEqual(config.routes.slice(-2),[{handle:'filesystem'},{src:'^/.*$',dest:'/404.html',status:404}]);
  assert(!config.routes.some(r=>r.src==='^/.*$' && !r.status));
});
test('production stages without domains and preview never requests production',()=>{
  const target={teamId:'team_test',teamSlug:'test',projectId:'prj_test'};
  assert(deployArgs('production',target,'/isolated').includes('--skip-domain'));
  assert(!deployArgs('preview',target,'/isolated').includes('--prod'));
  assert.throws(()=>deployArgs('production',{},'/isolated'),/Explicit/);
  assert.throws(()=>safeId('../other'),/Invalid/);
});
test('structured CLI output and protected binary responses are parsed without losing bytes',()=>{
  const deployment={id:'dpl_test',url:'https://fixture.vercel.app'};
  assert.deepEqual(deploymentResult(JSON.stringify({status:'ok',deployment})),deployment);
  assert.throws(()=>deploymentResult('{"status":"error"}'),/Missing/);
  const bytes=Buffer.from([0,255,128,13,10]);
  const response=parseHttpResponse(Buffer.concat([Buffer.from('HTTP/2 200\r\ncontent-type: image/png\r\n\r\n'),bytes]));
  assert.equal(response.status,200);assert.deepEqual(response.bytes,bytes);
});
test('command failures propagate and preparation primitives do not call hosting',async()=>{
  await assert.rejects(run(process.execPath,['-e','process.exit(7)']),e=>e.code===7);
  assert.equal((await run(process.execPath,['-e','process.stdout.write("local")'])).stdout,'local');
});
test('hosted verification checks exact bytes, CSV headers and real 404; rejects auth walls',async t=>{
  const root=await fixture(t),files=await inventory(root),release={staticFiles:files,routes:[]};
  const fake=async path=>{
    const f=files.find(f=>`/${f.path}`===path),bytes=Buffer.from(f?.path??'404.html');
    return {status:f?200:404,bytes,headers:path.endsWith('.csv')?{'content-type':'text/csv; charset=utf-8','content-disposition':'attachment; filename="summary.csv"','x-content-type-options':'nosniff'}:{}};
  };
  assert.equal((await checkHosted(release,root,'https://fixture.vercel.app',fake)).filesChecked,files.length);
  await assert.rejects(checkHosted(release,root,'https://fixture.vercel.app',async()=>({status:401,bytes:Buffer.from('auth'),headers:{}})),/authentication page/);
  await assert.rejects(checkHosted(release,root,'https://fixture.vercel.app',async p=>({...await fake(p),bytes:Buffer.from('wrong')})),/differs/);
  assert.equal(hash(Buffer.from('abc')),'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});

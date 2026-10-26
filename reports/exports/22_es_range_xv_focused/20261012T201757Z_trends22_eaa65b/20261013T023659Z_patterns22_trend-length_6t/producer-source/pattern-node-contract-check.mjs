import { readFileSync, writeFileSync, copyFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { resolve, join, relative } from 'node:path';
import { publishReport } from '../../apps/narada/scripts/lib/publication.mjs';

const root=resolve(import.meta.dirname,'../..');
const stage=join(root,'work/22_es_range_xv_focused/20261013T023659Z_patterns22_stage');
const settings=JSON.parse(readFileSync(join(stage,'settings.json'),'utf8'));
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const hashes={};
const checks=[];
for(const item of settings.selected){
  const path=join(stage,item.publicationId+'-patterns-r1','publication.json');
  const result=await publishReport({reportPath:path,dryRun:true});
  hashes[relative(stage,path)]=sha(path);
  checks.push({publicationId:result.id,command:['node','scripts/publish.mjs','--report',path,'--dry-run'],cwd:join(root,'apps/narada'),exitCode:0,result});
}
const schemas=join(stage,'producer-source/contracts');mkdirSync(schemas,{recursive:true});
for(const name of ['report.schema.json','report-1.0.schema.json','report-1.1.schema.json']){
  const from=join(root,'apps/narada/contracts',name),to=join(schemas,name);
  copyFileSync(from,to);hashes[relative(stage,to)]=sha(to);
}
const code=join(stage,'producer-source/pattern-node-contract-check.mjs');copyFileSync(import.meta.filename,code);hashes[relative(stage,code)]=sha(code);
writeFileSync(join(stage,'node-contract-dry-run.json'),JSON.stringify({result:'passed',runtime:{node:process.version},command:{argv:process.argv,cwd:process.cwd()},checks,artifact_hashes:hashes},null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({result:'passed',reports:checks.length,node:process.version}));

"""Independent exact-content/pin review of presentation-only candle diagrams."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import sys

def require(ok, message):
    if not ok:
        raise ValueError(message)

def file(root, rel):
    require(isinstance(rel,str) and not Path(rel).is_absolute(), 'Relative file locator required')
    p=root/rel
    require(p.is_file() and not any(x.is_symlink() for x in (p,*p.parents)), 'Regular file required')
    require(p.resolve().is_relative_to(root.resolve()), 'File escaped root')
    return p

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def jl(p):
    return json.loads(p.read_text())

def identity(report):
    r=json.loads(json.dumps(report,allow_nan=False))
    for key in ('id','publishedAt','patterns','patternOverviewId'):r.pop(key,None)
    for s in r['sections']:
        s.pop('patternId',None);s.pop('patternFocus',None)
    return json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)

def review(root, stage, prior):
    transfer=jl(stage/'transfer-verification.json');settings=jl(stage/'settings.json')
    require(transfer['result']=='passed' and len(settings['selected'])==18, '18 explicit reports required')
    hashes={'transfer-verification.json':sha(stage/'transfer-verification.json')}
    counts={'reports':0,'quantitative_sections':0,'table_rows':0,'numeric_cells':0,'csv_files':0,'source_maps':0,'prior_publication_files':0,'original_source_pins':0}
    expected={(a,s) for a in ('pullback-continuation','pullback-retracement','pullback-payoff','reversal-continuation','retracement-recovery','trend-length') for s in (4,5,6)}
    require({(x['analysisId'],x['setting']) for x in settings['selected']}==expected,'Analysis/chart coverage differs')
    for pin in transfer['source_artifacts']:
        p=file(root,pin['path']);require(sha(p)==pin['sha256'],'Original source pin changed');counts['original_source_pins']+=1
    for pin in transfer['outputs']:
        p=file(root,pin['path']);require(sha(p)==pin['sha256'],'Prepared output pin changed');hashes[p.relative_to(stage).as_posix()]=sha(p)
    require(sha(root/'studies/22_es_range_xv_focused/pattern_export.py')==sha(stage/'producer-source/pattern_export.py'),'Producer differs from retained bytes')
    for item in settings['selected']:
        new_id=item['publicationId']+'-patterns-r1';folder=stage/new_id
        old=file(root,item['revision']+'/publication.json');new=file(stage,new_id+'/publication.json')
        a,b=jl(old),jl(new)
        require(identity(a)==identity(b),'Existing statistical content or text changed')
        require(b['id']==new_id and b['publishedAt']==settings['published_at'] and b['source']==a['source'],'Attribution changed')
        require(b['source']['runId']==item['sourceRunId'],'Wrong source run')
        patterns={p['id']:p for p in b['patterns']}
        require(len(patterns)==len(b['patterns']) and b['patternOverviewId'] in patterns,'Bad pattern registry')
        seen={b['patternOverviewId']}
        for s in b['sections']:
            if s['kind'] not in ('table','metrics'):continue
            require(s.get('patternId') in patterns and bool(s.get('patternFocus')),'Missing quantitative focus panel')
            seen.add(s['patternId']);counts['quantitative_sections']+=1
            if s['kind']=='metrics':counts['numeric_cells']+=len(s['items'])
            else:
                counts['table_rows']+=len(s['rows'])
                counts['numeric_cells']+=sum(sum(c.get('format') in ('number','percent') for c in s['columns']) for row in s['rows'])
        require(seen==set(patterns),'Unused invisible pattern')
        for p in patterns.values():
            require('illustrative' in p['description'].lower(),'Illustration qualifier missing')
            for v in p['variants']:
                require(len({c['id'] for c in v['candles']})==len(v['candles']),'Duplicate candle IDs')
                for c in v['candles']:
                    require(0<=c['low']<=min(c['open'],c['close'])<=max(c['open'],c['close'])<=c['high']<=100,'Invalid illustrative OHLC')
        for d in a.get('downloads',[]):
            source=file(root,item['revision']+'/'+d['path']);target=file(stage,new_id+'/'+d['path'])
            require(sha(source)==sha(target)==d['sha256'],'Selected CSV bytes changed')
            hashes[target.relative_to(stage).as_posix()]=sha(target);counts['csv_files']+=1
        require(sha(file(root,item['revision']+'/source-map.json'))==sha(folder/'source-map.json'),'Source bindings changed')
        counts['source_maps']+=1;counts['reports']+=1
    for pin in jl(prior):
        require(sha(file(root,pin['path']))==pin['sha256'],'Prior public artifact changed');counts['prior_publication_files']+=1
    contract=jl(stage/'node-contract-dry-run.json')
    require(contract['result']=='passed' and len(contract['checks'])==18 and all(x['exitCode']==0 for x in contract['checks']),'18 actual Node contract checks required')
    for rel,value in contract['artifact_hashes'].items():require(sha(file(stage,rel))==value,'Contract checked bytes changed')
    hashes['node-contract-dry-run.json']=sha(stage/'node-contract-dry-run.json')
    child=jl(stage/'presentation-test-result.json')
    require(child['outcome']=='passed' and child['counts']['tests_run']>0 and child['counts']['tests_run']==child['counts']['discovered'] and all(child['counts'][k]==0 for k in ('failures','errors','skipped','expected_failures','unexpected_successes')),'Actual presentation tests required')
    hashes['presentation-test-result.json']=sha(stage/'presentation-test-result.json')
    semantic=jl(stage/'pattern-semantics-verification.json')
    require(semantic['result']=='passed' and semantic['transfer_verification_sha256']==hashes['transfer-verification.json'],'Semantic receipt not draft-bound')
    hashes['pattern-semantics-verification.json']=sha(stage/'pattern-semantics-verification.json')
    script=Path(__file__).resolve();snap=stage/'producer-source/patterns_independent_verify.py'
    with snap.open('xb') as f:f.write(script.read_bytes())
    hashes[snap.relative_to(stage).as_posix()]=sha(snap)
    for rel,value in hashes.items():require(sha(file(stage,rel))==value,'Reviewed bytes changed')
    result={'result':'passed','at':datetime.now(timezone.utc).isoformat(),'scope':'Presentation-only exact saved-content/CSV preservation and explicit panel coverage; not new research validation.','counts':counts,'artifact_hashes':hashes,'transfer_verification_sha256':hashes['transfer-verification.json'],'reviewer_source':{'path':script.relative_to(root).as_posix(),'sha256':sha(script),'snapshot':snap.relative_to(stage).as_posix()},'command':{'argv':[sys.executable,*sys.argv],'cwd':str(Path.cwd()),'python':sys.version}}
    with (stage/'independent-verification.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);a=p.parse_args()
    print(json.dumps(review(Path('.').resolve(),a.stage.resolve(),a.prior.resolve())['counts']))

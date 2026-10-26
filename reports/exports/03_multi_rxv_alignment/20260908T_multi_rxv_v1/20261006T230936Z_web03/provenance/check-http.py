from pathlib import Path
import json,urllib.request,urllib.error
root=Path('apps/narada');idx=json.loads((root/'public/publications/index.json').read_text());cat=json.loads((root/'content/studies.json').read_text());paths=['/']+['/studies/'+s['slug']+'/' for s in cat['studies']]+[p['href'] for p in idx['reports']]
for p in idx['reports']:
 bundle=json.loads((root/'public/publications'/p['id']/'report.json').read_text());paths+=['/publications/'+p['id']+'/report.json']+['/publications/'+p['id']+'/'+a['path'] for a in bundle['provenance']['assets']]
for p in paths:
 with urllib.request.urlopen('http://127.0.0.1:4173'+p) as r:assert r.status==200
missing=[]
for p in ['/studies/unknown-study/','/reports/unknown-publication/','/runs/private-evidence/']:
 try:urllib.request.urlopen('http://127.0.0.1:4173'+p);raise AssertionError(p)
 except urllib.error.HTTPError as e:assert e.code==404;missing.append({'path':p,'status':e.code})
record={'result':'passed','served_directory':'apps/narada/out','base_url':'http://127.0.0.1:4173','selected_http_targets_checked':len(paths),'missing_routes':missing,'studies':len(cat['studies']),'publications':len(idx['reports']),'assets':6}
Path('/private/tmp/abacus-phase3-http.json').write_text(json.dumps(record,indent=2)+'\n');print(record)

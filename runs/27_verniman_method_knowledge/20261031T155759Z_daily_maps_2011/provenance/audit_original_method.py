#!/usr/bin/env python3
"""Read-only exact preservation of the selected original method review."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path('/Users/pruthvi/Documents/projects/abacus')
RUN=ROOT/'runs/27_verniman_method_knowledge/20261023T174000Z_review27'
SHA='42058c98418d8446528e768972ae9a326438ede037aedecaea4465516e80ffad'
def check(base,row):
 p=base/row['path'];p.resolve().relative_to(base.resolve());raw=p.read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],str(p)
mraw=(RUN/'manifest.json').read_bytes();assert hashlib.sha256(mraw).hexdigest()==SHA
m=json.loads(mraw)
for row in m['artifacts']:check(RUN,row)
assert {p.relative_to(RUN).as_posix() for p in RUN.rglob('*') if p.is_file()}=={'manifest.json'}|{r['path'] for r in m['artifacts']}
for row in m['retained_external_sources']:check(ROOT,row)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
tracked=subprocess.check_output(['git','ls-files','-z',str(RUN.relative_to(ROOT))],cwd=ROOT).decode().rstrip('\0').split('\0');assert len(tracked)==80
for rel in tracked:assert subprocess.check_output(['git','show',head+':'+rel],cwd=ROOT)==(ROOT/rel).read_bytes(),rel
study=json.loads((ROOT/'studies/27_verniman_method_knowledge/study.json').read_text());assert study['reference_run']=='20261023T174000Z_review27'
print(json.dumps({'status':'passed','run':str(RUN.relative_to(ROOT)),'manifest_sha256':SHA,'manifest_bytes':len(mraw),'artifacts':len(m['artifacts']),'exact_run_files':len(m['artifacts'])+1,'retained_external_sources':len(m['retained_external_sources']),'tracked_files_match_git_head':head,'selected_reference_unchanged':True,'scope':'Read-only exact byte preservation, not historical source or method revalidation.'},indent=2))

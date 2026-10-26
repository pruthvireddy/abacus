"""Presentation-only corrections from independent saved-evidence review."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, html, json, shutil
stage=Path(__file__).resolve().parents[1]
def pin(p):
 return {'path':str(p.relative_to(stage)), 'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
paths=['report.md','report.html','advice.md','publication.json','source-bindings.json','publication-source-map.json']
before=[pin(stage/p) for p in paths]
old='Primary buckets require every expected source minute and one contract. Feature readiness is recorded on native 5m; mapped decision eligibility is in signal flow. Unknown missingness is not compressed.'
new='Primary buckets require every expected source minute and one contract. Development readiness counts usable signal slots with a valid mapped cloud for both intervals. Warmup-only native 5m readiness is retained; warmup-only 3m readiness is undefined. Unknown missingness is not compressed.'
synthesis=('The pooled H15 signed terminal means do not establish positive continuation under the prespecified four-week uncertainty calculation. Mean adverse excursion exceeds mean favorable excursion in every pooled primary cell. Pooled intervals do not describe every side or session: negative subgroup findings and block-length sensitivities remain in the saved tables. Equal-active terminal contrasts are inconclusive; some excursion contrasts differ. Coverage improves markedly toward 2020, and early GC annual cohorts are sparse, so pooled evidence does not establish stability across years. Exact review references: provenance/reviews/interpretation-review.json; coverage S1-T00, primary and side scorecards S1-T02, annual/session S1-T04, uncertainty S1-bootstrap and contrasts S1-comparisons.')
qualification=('Verified published partition bytes and retained release lineage support this descriptive analysis. Original raw source reconstruction could not be certified because retained mapping/definition prerequisites are unavailable; native TradingView equivalence and off-device backup verification were not executed. These qualifications are distinct from the passed consumed-input and scientific checks.')
publication=json.loads((stage/'publication.json').read_text())
for section in publication['sections']:
 if section['id']=='coverage':
  assert old in section['description'] or new in section['description']
  section['description']=section['description'].replace(old,new)
 if section['id']=='findings' and synthesis not in section['body']: section['body']=synthesis+'\n\n'+section['body']
 if section['id']=='limitations' and qualification not in section['body']: section['body']+='\n\n'+qualification
 if section['id'].startswith('examples-'):
  section['alt']=section['alt'].replace('six product/candle panels','fifteen product/example panels')
if qualification not in publication['notes']: publication['notes'].append(qualification)
(stage/'publication.json').write_text(json.dumps(publication,indent=2,ensure_ascii=False)+'\n')
for name in ('report.md','report.html'):
 p=stage/name; text=p.read_text(); assert old in text or new in text
 text=text.replace(old,new)
 if name.endswith('.md') and synthesis not in text:
  text=text.replace('## Findings\n\n','## Findings\n\n'+synthesis+'\n\n',1)
  text=text.replace('## Coverage and limitations\n\n','## Coverage and limitations\n\n'+qualification+'\n\n',1)
  text+='\nExact saved uncertainty and contrasts: [S1-bootstrap](tables/S1-bootstrap.csv), [S1-comparisons](tables/S1-comparisons.csv).\n'
 elif name.endswith('.html'):
  text=text.replace('<section><h2>Stage 1 development findings</h2>','<section><h2>Stage 1 development findings</h2>\n<p>'+html.escape(synthesis)+'</p>',1)
  marker='<section><h2>Coverage and interpretation limits</h2>'
  assert marker in text; text=text.replace(marker,marker+'\n<p>'+html.escape(qualification)+'</p>',1)
  text=text.replace('</body>','<p>Exact saved uncertainty and contrasts: <a href="tables/S1-bootstrap.csv">S1-bootstrap</a>, <a href="tables/S1-comparisons.csv">S1-comparisons</a>.</p></body>')
  text=text.replace('six product/candle panels','fifteen product/example panels')
 p.write_text(text)
p=stage/'advice.md'; text=p.read_text(); text=text.replace('Preserve this slow-touch baseline for Stage 2.',synthesis+'\n\n'+qualification+'\n\nPreserve this slow-touch baseline for Stage 2.',1);p.write_text(text)
bindings=json.loads((stage/'source-bindings.json').read_text())
bindings['publication_sha256']=pin(stage/'publication.json')['sha256']
(stage/'source-bindings.json').write_text(json.dumps(bindings,indent=2,ensure_ascii=False)+'\n')
shutil.copyfile(stage/'source-bindings.json',stage/'publication-source-map.json')
receipt={'status':'completed_pending_independent_reverification','time':datetime.now(timezone.utc).isoformat(),'scope':'Presentation-only caption, interpretation qualifications, exact uncertainty links and example alt text. No numeric cells, claims, plots, downloads, selectors, settings, ledgers or estimators changed. Original frozen renderer and failed coverage checker remain retained.','sources':[pin(stage/'provenance/reviews/interpretation-review.json')], 'before':before,'after':[pin(stage/p) for p in paths]}
(stage/'provenance/presentation-correction.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'files':len(paths)}))

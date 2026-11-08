"""Read-only bounded Phase 2 provenance and consistency checks.

No HTTP, no unrestricted target table reads, no research recalculation.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime
from decimal import Decimal
import csv
import hashlib
import json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
STAGE=ROOT/'work/29_verniman_level_reconstruction/phase2_20261030T222323Z'
ALLOWED={'2026-10-01','2026-10-02','2026-10-05'}

def require(value,message):
    if not value:raise ValueError(message)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    freeze=json.loads((STAGE/'protocol-freeze.json').read_text())
    for path,expected in freeze['sha256'].items():
        require(digest(ROOT/path)==expected,'Frozen input changed: '+path)
    neutral=json.loads((STAGE/'neutral-baselines.json').read_text())
    require(neutral['all_three_captured_before_any_target_review'],'Missing neutral capture gate')
    require({r['date'] for r in neutral['observations']}==ALLOWED,'Wrong baseline dates')
    frozen_at=datetime.fromisoformat(freeze['frozen_at'])
    for r in neutral['observations']:
        require(len(r['frozen_values'])==19 and r['readiness']=='19/19','Incomplete baseline')
        require(r['last_included_open'].startswith(r['date']+'T09:20:'),'Wrong final bar open')
        require(r['last_included_close'].startswith(r['date']+'T09:25:'),'Wrong cutoff')
        require(digest(ROOT/r['fresh_image'])==r['sha256'],'Changed neutral image')
        require(datetime.fromisoformat(r['capture_timestamp'])>frozen_at,'Capture preceded protocol freeze')
    selected=json.loads((STAGE/'source-selection-manifest.json').read_text())
    require(datetime.fromisoformat(selected['selection_started_at'])>datetime.fromisoformat(neutral['completed_at']),'Targets selected before all neutral baselines')
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    require(set(manifest['authorized_target_dates'])==ALLOWED,'Wrong source dates')
    require(digest(ROOT/manifest['release']['manifest_path'])==manifest['release']['manifest_sha256'],'Release manifest hash mismatch')
    require(digest(ROOT/manifest['selection_manifest']['path'])==manifest['selection_manifest']['sha256'],'Selection record changed')
    sources={s['source_id']:s for s in manifest['sources']}
    require(len(sources)==len(manifest['sources']),'Duplicate source IDs')
    checked=set()
    for case in manifest['cases']:
        entry=case['intake_observation'];path=ROOT/entry['path']
        require(digest(path)==entry['sha256'],'Original intake bytes changed');checked.add(str(path))
    for source in sources.values():
        require(source['session_date'] in ALLOWED,'Unauthorized source date')
        require(source.get('available_at') is None,'Historical availability was invented')
        entries=source.get('bytes') or []
        if isinstance(entries,dict):entries=[entries]
        if source.get('path') and source.get('sha256'):
            entries=entries+[{'path':source['path'],'sha256':source['sha256']}]
        for entry in entries:
            path=ROOT/entry['path'];require(digest(path)==entry['sha256'],'Source bytes changed: '+entry['path']);checked.add(str(path))
    inventory=json.loads((HERE/'level-inventory.json').read_text())
    levels=inventory['levels'];ids={r['level_id'] for r in levels}
    require(len(ids)==len(levels)==143,'Wrong/duplicate inventory count')
    for row in levels:
        require(row['session_date'] in ALLOWED,'Unauthorized level date')
        require(row['source_id'] in sources,'Unknown level source')
        require(row['session_date']==sources[row['source_id']]['session_date'],'Cross-date source reference')
        require(row['available_at'] is None,'Invented level availability')
        lo,hi=Decimal(row['price_low']),Decimal(row['price_high'])
        require(lo.is_finite() and hi.is_finite() and lo<=hi,'Invalid interval')
        require(row['price_basis'] in {'printed','aligned_axis_badge','axis_estimate'},'Unknown price-reading basis')
        if row['price_basis']=='axis_estimate':require(lo<hi,'Axis estimate has false point precision')
        require(row['candidate_explanations'] and row['competing_explanations'] and row['unresolved_questions'],'Missing interpretation qualifications')
    bases={r['date']:r['frozen_values'] for r in neutral['observations']}
    by_id={r['level_id']:r for r in levels};counts=Counter()
    with (HERE/'baseline-comparison.csv').open(newline='') as inp:
        for row in csv.DictReader(inp):
            require(row['level_id'] in by_id,'Unknown comparison level')
            level=by_id[row['level_id']];require(row['session_date']==level['session_date'],'Wrong comparison date')
            p=Decimal(row['baseline_price']);lo=Decimal(level['price_low']);hi=Decimal(level['price_high'])
            require(p==Decimal(str(bases[row['session_date']][row['baseline_family']])),'Wrong baseline value')
            require(Decimal(row['distance_to_source_interval_points'])==max(lo-p,p-hi,Decimal(0)),'Wrong comparison distance')
            counts[row['level_id']]+=1
    require(set(counts)==ids and set(counts.values())=={19},'Each occurrence must retain all19 alternatives')
    require(any(r['original_label']=='VPOC 6691' for r in levels),'Lost plan anomaly')
    require(any(r['original_label']=='VPOC 7691 magnet' for r in levels),'Lost conflicting image')
    require(any(r['original_label']=='PBT-ETH magnet' and r['price_low']=='7746.75' for r in levels),'Lost plotted PBT precision')
    for day in ALLOWED:
        require((HERE/'cases'/f'{day}.md').is_file(),'Missing case')
        for ext in ['png','svg']:require((HERE/'figures'/f'{day}-comparison.{ext}').stat().st_size>1000,'Missing authored illustration')
    phase1=ROOT/'work/29_verniman_level_reconstruction/phase1_20261030'
    old=json.loads((phase1/'artifact-hashes.json').read_text())
    for item in old['artifacts']:require(digest(phase1/item['path'])==item['sha256'],'Phase1 artifact changed')
    summary={'status':'passed','checks':['protocol/input pins','baseline before target gate','three-date scope','source hashes','null historical timing','stable references','interval precision','all19 descriptive distances','source conflicts retained','case/figure presence','Phase1 artifact preservation'],
             'source_count':len(sources),'source_paths_hashed':len(checked),'level_occurrences':len(levels),'comparison_rows':sum(counts.values()),'phase1_artifacts_verified':len(old['artifacts']),
             'limits':'Integrity/consistency only. Not independent OCR, historical-availability proof, Pine compilation, algorithm validation or scientific validity.'}
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

"""Save input/feature quality evidence without executing any signal cohort."""
import argparse
from datetime import datetime,timezone
import html
import json
from pathlib import Path
import shutil
import subprocess
import sys
import importlib.metadata
import numpy as np
import pandas as pd
from abacus_bhishma.paths import load_workspace_paths
from abacus_bhishma.vp_hvn_loader import load_release
from abacus_bhishma.provenance import sha256_file as sha256
if __package__:
    from .evidence import DATASET_ID, dump, PACKAGE_SOURCE_PATHS
else:
    from evidence import DATASET_ID, dump, PACKAGE_SOURCE_PATHS


def markdown_table(frame):
    columns=list(frame.columns)
    def cell(x):
        if isinstance(x,float):return f'{x:,.3f}'
        return str(x).replace('|','/')
    return '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+ '\n'.join('| '+' | '.join(cell(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None))+'\n'


def prepare(stage,plot_python=None):
    paths=load_workspace_paths();root=paths.publication_root;workspace=paths.workspace_root
    study=workspace/'studies/14_asia_session_vp_levels'
    lock=json.loads((study/'inputs.lock.json').read_text())
    identity=lock.get('derived_feature_release',{})
    if identity.get('status')!='published_pinned':raise ValueError('pin delivered release before preparation')
    manifest=root/identity['manifest_path']
    if sha256(manifest)!=identity['sha256']:raise ValueError('delivered feature manifest mismatch')
    feature=json.loads(manifest.read_text())
    for r in feature['output_files']:
        if sha256(root/r['path'])!=r['sha256']:raise ValueError(f"feature partition changed: {r['path']}")
    stage=stage.resolve();stage.mkdir(parents=True,exist_ok=False)
    (stage/'tables').mkdir();(stage/'figures').mkdir();(stage/'source').mkdir()
    session=load_release(root,'1.0.0','sessions').to_table().to_pandas()
    rhythm=load_release(root,'1.0.0','rhythm').to_table().to_pandas()
    cols=['session_date','minute','overnight_complete','overnight_contract_clean','hvn_complete','hvn_contract_clean',
          'reference_complete','reference_contract_clean','source_degraded','hvn_source_degraded','reference_source_degraded']
    snaps=load_release(root,'1.0.0').to_table(columns=cols).to_pandas()
    snaps['year']=snaps.session_date.str[:4].astype(int)
    signal_clock=(snaps.minute>=119)&(snaps.minute<359)
    snaps['potential_next_open_window']=signal_clock
    snaps['strict_overnight_input']=signal_clock & snaps.overnight_complete & snaps.overnight_contract_clean & ~snaps.source_degraded
    snaps['strict_hvn_reference_input']=snaps.strict_overnight_input & snaps.hvn_complete & snaps.hvn_contract_clean & snaps.reference_complete & snaps.reference_contract_clean & ~snaps.hvn_source_degraded & ~snaps.reference_source_degraded
    quality=session.groupby('year').agg(source_dates=('session_date','size'),source_rows=('source_rows','sum'),
                                      complete_futures_sessions=('complete','sum'),evening_minutes=('evening_rows','sum'),
                                      missing_evening_minutes=('missing_evening_minutes','sum'),outside_futures_rows=('outside_futures_rows','sum'))
    quality['complete_six_hour_evenings']=session.assign(full=session.evening_rows.eq(360)).groupby('year').full.sum()
    quality['dates_without_futures_bars']=session.assign(empty=session.futures_rows.eq(0)).groupby('year').empty.sum()
    quality['holiday_labelled_dates']=session.assign(holiday=session.holiday_names.ne('')).groupby('year').holiday.sum()
    quality=quality.join(snaps.groupby('year')[['potential_next_open_window','strict_overnight_input','strict_hvn_reference_input']].sum()).reset_index()
    quality.to_csv(stage/'tables/quality_by_year.csv',index=False)
    session.to_csv(stage/'tables/session_quality.csv',index=False)
    seasonal=rhythm[rhythm.complete].groupby(['year','season','bin_minute']).agg(
        sessions=('session_date','size'),mean_volume=('volume','mean'),median_volume=('volume','median'),
        mean_range_points=('range_points','mean'),median_range_points=('range_points','median'),
        mean_intrabin_abs_close_change=('absolute_close_change','mean')).reset_index()
    seasonal.to_csv(stage/'tables/rhythm_by_year_season.csv',index=False)
    pooled=rhythm[rhythm.complete & rhythm.year.between(2020,2023)].groupby(['season','bin_minute']).agg(
        sessions=('session_date','size'),mean_volume=('volume','mean'),mean_range_points=('range_points','mean')).reset_index()
    pooled.to_csv(stage/'tables/rhythm_development.csv',index=False)
    # Rendering consumes the saved table; analysis stays in the locked workspace.
    plot_command=None
    if plot_python:
        plot_command=[str(plot_python),str(study/'render_chart.py'),'--stage',str(stage)]
        subprocess.run(plot_command,check=True)
    visual_md='\n![Volume and range from 18:00 onward](figures/volume_rhythm.svg)\n\n' if plot_python else '\n'+markdown_table(pooled)+'\n'
    visual_html='<img src="figures/volume_rhythm.svg" alt="Mean 15-minute volume and range, with EST and EDT separate">' if plot_python else pooled.to_html(index=False,escape=True,border=0)
    summary={'kind':'feature_preparation_only','study_outcomes_computed':False,'primary_comparison_frozen':False,
             'setup_1_clarification':'Required: buy at POC after an upper excursion, or sell on re-entry targeting POC; mirror lower cases.',
             'feature_dataset':DATASET_ID,'feature_manifest_sha256':sha256(manifest),
             'snapshot_rows':feature['rows'],'source_dates':len(session),
             'source_rows':int(quality.source_rows.sum()),'candidate_rows':sum(r['rows'] for r in feature['output_files'] if r['table']=='candidates'),
             'complete_six_hour_evenings':int(quality.complete_six_hour_evenings.sum()),
             'strict_overnight_input_minutes':int(quality.strict_overnight_input.sum()),
             'strict_hvn_reference_input_minutes':int(quality.strict_hvn_reference_input.sum()),
             'window_interpretation':'Potential feature availability before signals whose next open lies in 20:00-00:00; no signal or future-path qualification inferred.',
             'limitations':feature['limitations']}
    dump(stage/'metrics.json',summary);shutil.copyfile(study/'inputs.lock.json',stage/'inputs.lock.json')
    dump(stage/'config.json',{'scope':'Independent feature preparation and synthetic infrastructure','feature_contract':feature['feature_protocol'],
                             'primary_study_protocol_status':'Not frozen, required setup 1 answer pending','full_study_executed':False})
    text=(f'# Asia session VP levels — feature preparation\n\n'
          f'**The MAE/MFE study has not run. Setup 1 clarification is pending and the primary comparison remains unfrozen.**\n\n'
          f'The delivered NQ feature release contains {summary["snapshot_rows"]:,} evening snapshots and {summary["candidate_rows"]:,} candidate records in raw and adjusted frames. '
          f'It consumes {summary["source_rows"]:,} source observations across {summary["source_dates"]:,} observed dates.\n\n'
          'The table below measures input availability. Potential minutes are observations before a possible next-open entry, not trade signals. '
          'Strict overnight and HVN/reference flags have different lookbacks; incomplete source observations are retained and never filled. '
          'No signal opportunity funnel, MAE/MFE estimate, matched-control result or setup conclusion exists yet.\n\n'+
          markdown_table(quality)+ visual_md+
          'The chart uses saved 2020–2023 complete 15-minute bins, with EST/EDT kept separate. '
          'It measures the fixed New York clock; it does not attribute changes to Asian exchange opens. '
          'The absolute-close-change column in the seasonal evidence contains within-bin observed close changes, excluding the bin boundary.\n\n'
          'Source hashes, raw/adjusted lineage, arithmetic, timing and deterministic pilot checks accompany this preparation. '
          'One-minute OHLCV cannot certify tick profiles, transient zones, exact touch fills or intraminute order. '
          'The weekly exchange-session boundary and equal-strength sort adaptation are disclosed; external TradingView parity is unverified.\n\n'
          'Required next step: resolve the setup 1 direction, freeze the whole study protocol, implement the cohort orchestration and execute the declared horizons, controls, robustness and reports. '
          'This preparation is staged work, not a completed immutable research run.\n')
    (stage/'report.md').write_text(text)
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Asia VP feature preparation</title>
<style>body{{font:16px/1.55 system-ui;color:#193247;background:#f6f8fa;max-width:1200px;margin:50px auto;padding:0 24px}}h1{{font-size:36px}}.status{{padding:20px;background:#fff1d4;border-left:5px solid #bf8122}}table{{border-collapse:collapse;font-size:12px;background:white}}td,th{{padding:7px;border-bottom:1px solid #dde5eb;text-align:right}}.scroll{{overflow:auto}}img{{width:100%;max-width:980px}}p{{max-width:850px}}</style>
<h1>Asia session VP levels</h1><p class="status">Feature preparation only. The MAE/MFE study has not run; setup 1 clarification is pending.</p>
<p>{summary['snapshot_rows']:,} evening snapshots · {summary['candidate_rows']:,} candidate records · {summary['source_rows']:,} source observations. Saved raw and adjusted calculations remain separate.</p>
<h2>Input availability by year</h2><p>These are feature minutes and data-quality counts, not signals or outcome results. Strict overnight and HVN/reference histories differ.</p>
<div class="scroll">{quality.to_html(index=False,escape=True,border=0)}</div><h2>Evening volume and range pattern</h2>{visual_html}
<p>Saved complete bins from 2020–2023. The fixed New York window includes the 18:00–20:00 context. No exchange-open attribution is inferred.</p>
<h2>Limits and next step</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in feature['limitations'])}</ul>
<p>Resolve setup 1, freeze the comparison family, complete event orchestration, then execute horizons, controls and robustness checks. No setup conclusion is available yet.</p>
<p><a href="report.md">Markdown report</a> · <a href="tables/quality_by_year.csv">Saved yearly counts</a> · <a href="tables/rhythm_by_year_season.csv">Saved rhythm evidence</a> · <a href="preparation.manifest.json">Provenance</a></p></html>'''
    (stage/'report.html').write_text(page)
    source_paths=[*study.glob('*.py'),*study.glob('*.md'),study/'study.yaml',study/'inputs.lock.json',
                  *study.glob('src/*.py'),*study.glob('tests/*.py'),workspace/'uv.lock']
    source_paths.extend(workspace/r['path'] for r in feature['code'])
    source_paths.extend(workspace/path for path in PACKAGE_SOURCE_PATHS)
    source_paths.append(workspace/'packages/bhishma/src/abacus_bhishma/vp_hvn_loader.py')
    source_paths.extend([root/feature['indicator_source']['path'],workspace/feature['feature_protocol']['path']])
    source_records=[]
    for p in sorted(set(source_paths)):
        relative=p.relative_to(workspace) if p.is_relative_to(workspace) else Path('publication')/p.relative_to(root)
        dest=stage/'source'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        source_records.append({'path':str(relative),'sha256':sha256(p)})
    versions={name:importlib.metadata.version(name) for name in ('numpy','pyarrow','pandas')}
    dump(stage/'environment.json',{'python':sys.version,'packages':versions,'lock_sha256':sha256(workspace/'uv.lock')})
    artifacts=[{'path':str(p.relative_to(stage)),'sha256':sha256(p),'bytes':p.stat().st_size} for p in sorted(stage.rglob('*')) if p.is_file()]
    dump(stage/'preparation.manifest.json',{'study_id':study.name,'stage_id':stage.name,'status':'awaiting_setup_1_answer',
         'created_utc':datetime.now(timezone.utc).isoformat(),'git_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=workspace,text=True).strip(),
         'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=workspace,text=True),'working_tree_dirty':True,
         'source_snapshot':source_records,'artifacts':artifacts,'feature_manifest':identity,'full_study_executed':False,
         'plot_command':plot_command,
         'command':f'UV_CACHE_DIR=work/.uv-cache ./scripts/uv run --locked --no-sync python studies/{study.name}/run.py --prepare-features --stage {stage.relative_to(workspace)}'})
    return stage


def main():
    parser=argparse.ArgumentParser(description='Independent feature preparation; primary execution waits for setup 1 clarification.')
    parser.add_argument('--prepare-features',action='store_true');parser.add_argument('--stage',type=Path)
    parser.add_argument('--plot-python',type=Path,help='Optional existing presentation runtime with ReportLab; consumes saved CSV only')
    args=parser.parse_args()
    if not args.prepare_features or args.stage is None:
        parser.error('Required setup 1 answer is pending; only --prepare-features --stage is currently available. No study outcomes have been run.')
    print(prepare(args.stage,args.plot_python))

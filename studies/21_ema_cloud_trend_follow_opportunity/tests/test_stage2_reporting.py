"""Deterministic selection and full synthetic private report transfer fixtures."""
import importlib.util
import itertools
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage2_reporting import select_examples, prepare_examples, render_bundle
from src.stage2_reconcile import reconcile_examples, verify_publication
from src.stage2_statistics import (summarize_branches, quantiles_branches, stability_branches,
    signal_flow_branches, support_roster, coverage_columns, geometry_membership,
    episode_pair_metrics, episode_summary, union_summary)
from src.stage2_comparisons import branch_contrasts, paired_uncertainty
from src.stage2_contract import TABLES
from src.reconcile import sha256
from test_stage2_reconcile import synthetic_cell


def synthetic_saved_stage(stage):
    """Create wholly synthetic six-cell evidence; no retained market inputs."""
    stage=Path(stage)
    (stage/'tables').mkdir(parents=True)
    records=[]
    outcomes_all=[]
    flows=[]
    geometries=[]
    pairs=[]
    unions=[]
    rosters=[]
    sessions=set()
    coverage=[]
    for p,i in itertools.product(('ES','GC','NQ'),(3,5)):
        bars,tech,events,outcomes,members,projected=synthetic_cell(p,i)
        for role,frame in {'technical':tech,'events':events,'outcomes':outcomes,'pairs':members['pairs']}.items():
            path=stage/f'{p}_{i}_{role}.parquet'
            frame.to_parquet(path,index=False)
            records.append(dict(role=role,product=p,interval_minutes=i,path=str(path.resolve()),
                bytes=path.stat().st_size,sha256=sha256(path),row_count=len(frame)))
        outcomes_all.append(outcomes)
        flows.append(signal_flow_branches(tech,events,outcomes))
        geometries.append(geometry_membership(members['membership']))
        pairs.append(members['pairs'])
        unions.append(union_summary(members['membership'],members['union'],outcomes,projected))
        roster,ss=support_roster(tech)
        rosters.append(roster)
        sessions.update(ss)
        for year in (2018,2019,2020):
            coverage.append(dict(product=p,interval_minutes=i,year=year,split='development',
                scheduled_slots=len(bars) if year==2018 else 0,usable_slots=len(bars) if year==2018 else 0,
                feature_ready_slots=len(bars) if year==2018 else 0,mapped_ready_slots=len(bars) if year==2018 else 0,
                ready_share=1. if year==2018 else None,ready_sessions=1 if year==2018 else 0))
    (stage/'events.manifest.json').write_text(json.dumps(dict(records=records)))
    combined=pd.concat(outcomes_all,ignore_index=True)
    pairframe=pd.concat(pairs,ignore_index=True)
    metrics=episode_pair_metrics(pairframe,combined)
    stability=coverage_columns(stability_branches(combined,sorted(sessions)),pd.concat(rosters,ignore_index=True))
    # Small replicate count here tests saved presentation; it never represents a research run.
    contrasts=pd.concat([branch_contrasts(combined),paired_uncertainty(combined,resamples=2,block_lengths=(1,4,8))],ignore_index=True)
    frames={
        'S2-T00':pd.DataFrame(coverage),'S2-T01':pd.concat(flows,ignore_index=True),
        'S2-T02':summarize_branches(combined,('all','same_session','uninterrupted')),
        'S2-T03':quantiles_branches(combined),'S2-T04':stability[~stability.period_kind.isin(['week','month'])],
        'S2-T05':stability[stability.period_kind.isin(['week','month'])],
        'S2-T07':pd.concat(geometries,ignore_index=True),'S2-T08':contrasts,
        'S2-T09':episode_summary(pairframe,metrics),'S2-T10':pd.concat(unions,ignore_index=True)}
    for key,frame in frames.items(): frame.to_csv(stage/'tables'/TABLES[key],index=False,float_format='%.17g')
    prepare_examples(stage)
    return records


class Stage2SelectionTests(unittest.TestCase):
    def test_six_classes_unresolved_excludes_observed_samebar_and_extrema_ties(self):
        _,tech,events,outcomes,members,_=synthetic_cell()
        examples=select_examples(tech,events,outcomes,members['pairs']).set_index('kind')
        self.assertEqual(len(examples),6)
        self.assertTrue(examples.selection_status.eq('selected').all())
        pair=members['pairs'].set_index('shared_episode_id').loc[examples.loc['unresolved','shared_episode_id']]
        self.assertFalse(pair.same_bar_slow_contact)
        self.assertTrue(pd.isna(pair.strictly_later_slow_contact))
        bad=members['pairs'].copy()
        bad.loc[bad.pair_relation.eq('fast_only'),'same_bar_slow_contact']=True
        unavailable=select_examples(tech,events,outcomes,bad).set_index('kind')
        self.assertEqual(unavailable.loc['unresolved','selection_status'],'unavailable')
        complete=outcomes.query("horizon == 15 and status == 'completed'")
        expected=complete.sort_values(['mae','timestamp','event_id'],ascending=[False,True,True]).iloc[0]
        self.assertEqual(examples.loc['high_adverse','event_id'],expected.event_id)
        self.assertEqual(examples.loc['rejected','reference_price'],112.)

    def test_paths_are_capped_scoped_and_source_values_are_reconciled(self):
        with tempfile.TemporaryDirectory() as directory:
            stage=Path(directory)
            synthetic_saved_stage(stage)
            paths=pd.read_parquet(stage/'tables/selected-example-paths.parquet')
            self.assertTrue(paths.relative_slot.between(-10,15).all())
            self.assertLessEqual(paths.groupby(['example_id','segment_id']).size().max(),26)
            self.assertTrue(pd.to_datetime(paths.timestamp,utc=True).dt.tz_convert('America/New_York').dt.year.eq(2018).all())
            _,tech,events,outcomes,members,_=synthetic_cell()
            result=reconcile_examples(tech,events,outcomes,members['pairs'],stage/'tables'/TABLES['S2-T06'],paths)
            self.assertEqual(result['classes'],6)
            corrupted=paths.copy()
            corrupted.loc[corrupted.example_id.str.startswith('S2-T06|ES|5|'),'close']+=1.
            with self.assertRaises(ValueError):
                reconcile_examples(tech,events,outcomes,members['pairs'],stage/'tables'/TABLES['S2-T06'],corrupted)
            with self.assertRaisesRegex(ValueError,'overwrite'):
                prepare_examples(stage)


@unittest.skipUnless(importlib.util.find_spec('matplotlib') is not None,'Separately inventoried existing plotting dependencies required')
class Stage2FullReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.stage=Path(cls.directory.name)/'20261011T002602Z_s2_fixture'
        synthetic_saved_stage(cls.stage)
        cls.render=render_bundle(cls.stage)
        retained=os.environ.get('STUDY21_STAGE2_RENDER_RETAIN')
        if retained:
            destination=Path(retained)
            if destination.exists(): raise ValueError('retained synthetic render overwrite refused')
            shutil.copytree(cls.stage,destination)
        cls.original=(cls.stage/'publication.json').read_text()
        cls.binding_original=(cls.stage/'source-bindings.json').read_text()

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    def tearDown(self):
        (self.stage/'publication.json').write_text(self.original)
        (self.stage/'source-bindings.json').write_text(self.binding_original)

    def mutate_publication(self,callback):
        pub=json.loads(self.original)
        callback(pub)
        path=self.stage/'publication.json'
        path.write_text(json.dumps(pub))
        binding=json.loads(self.binding_original)
        binding['publication_sha256']=sha256(path)
        (self.stage/'source-bindings.json').write_text(json.dumps(binding))

    def test_rendered_six_pngs_all_public_cells_downloads_claims_and_coverage_bindings(self):
        self.assertEqual((self.render['figures'],self.render['claims'],self.render['downloads']),(6,6,4))
        self.assertEqual(verify_publication(self.stage)['status'],'passed')
        figures=list((self.stage/'figures').glob('*.png'))
        self.assertEqual(len(figures),6)
        self.assertTrue(all(p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') and p.stat().st_size<=2*1024*1024 for p in figures))
        bindings=json.loads(self.binding_original)
        coverage=[s for f in bindings['figures'] for s in f['sources'] if 'S2-T00' in s['source_artifact']]
        self.assertEqual(len(coverage),1)
        self.assertNotIn('row_ids',coverage[0])
        self.assertEqual(len(coverage[0]['data_rows_1_based']),18)
        self.assertLessEqual((self.stage/'publication.json').stat().st_size,96*1024)

    @unittest.skipUnless(shutil.which('node'),'Existing Node runtime required for private publisher contract fixture')
    def test_actual_private_publisher_dry_run(self):
        app=Path(__file__).resolve().parents[3]/'apps/narada'
        result=subprocess.run(['node','scripts/publish.mjs','--report',str(self.stage/'publication.json'),'--dry-run'],cwd=app,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['dryRun'])

    def test_corrupt_public_numeric_cell_rejected_even_with_updated_publication_pin(self):
        self.mutate_publication(lambda p: next(s for s in p['sections'] if s['id']=='branch-primary')['rows'][0].update(accepted=999))
        with self.assertRaises(ValueError): verify_publication(self.stage)

    def test_false_aggregate_headline_and_missing_claim_binding_are_rejected(self):
        self.mutate_publication(lambda p:p.update(summary='All six effects conclusively establish profit.'))
        with self.assertRaisesRegex(ValueError,'headline'): verify_publication(self.stage)
        (self.stage/'publication.json').write_text(self.original)
        binding=json.loads(self.binding_original)
        binding['claims']=binding['claims'][1:]
        (self.stage/'source-bindings.json').write_text(json.dumps(binding))
        with self.assertRaisesRegex(ValueError,'six primary claims'): verify_publication(self.stage)

    def test_download_original_string_mutation_is_rejected_with_fresh_byte_pins(self):
        binding=json.loads(self.binding_original)
        item=binding['downloads'][0]
        path=self.stage/item['path']
        original=path.read_text()
        try:
            frame=pd.read_csv(path,dtype=str,keep_default_na=False)
            frame.loc[0,'accepted']='999.0'
            frame.to_csv(path,index=False)
            item['sha256']=sha256(path)
            pub=json.loads(self.original)
            next(d for d in pub['downloads'] if d['id']==item['download'])['sha256']=item['sha256']
            (self.stage/'publication.json').write_text(json.dumps(pub))
            binding['publication_sha256']=sha256(self.stage/'publication.json')
            (self.stage/'source-bindings.json').write_text(json.dumps(binding))
            with self.assertRaisesRegex(ValueError,'exact saved string'): verify_publication(self.stage)
        finally: path.write_text(original)


if __name__=='__main__': unittest.main()

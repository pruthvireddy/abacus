"""Saved-table rendering, exact transfer, bounds and real publisher dry run."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.stage3_reporting import CELLS, TABLES, render_bundle
from src.stage3_reconcile import verify_publication
from src.stage3_reference import gate_grid, gate_id, HORIZONS
from src.stage3_statistics import summaries,grid_comparisons,neighborhoods,period_effects
from src.stage3_selection import validation_decisions
from tests.test_stage3_reference import config


def synthetic_paths(product,interval,branch,gate,phase,shift=0):
    rows=[]
    year={"development":2019,"validation":2022,"final":2024,"recent":2026}[phase]
    for h in HORIZONS:
        for i in range(6):
            timestamp=pd.Timestamp(f"{year}-0{1+i}-10T14:00Z")
            day=timestamp.date();week=(day-pd.Timedelta(days=day.weekday())).isoformat()
            delta=(-.3+(.16 if i%2 else -.04)+shift)*(h/15)**.4
            mfe=(.8+shift*.1)*(h/15)**.5;mae=(1.1-shift*.1)*(h/15)**.5
            rows.append(dict(product=product,interval_minutes=interval,touch_mode=branch,gate_id=gate["gate_id"],horizon=h,horizon_minutes=h*interval,
                direction=1,side="Buy",event_id=f"{product}|{interval}|{branch}|{i}",signal_idx=i,timestamp=timestamp,entry_at=timestamp+pd.Timedelta(minutes=interval),
                status="completed",censor_reason="",score_eligible=True,atr_support=True,start_embargo=False,endpoint_purge=False,entry_atr=2.,fold_id=str(year)+("H1" if i<3 else "H2"),
                session=str(day),week=week,year=year,month=timestamp.strftime("%Y-%m"),hour=9,time_stratum="US",elapsed_minutes=h*interval,
                same_session=True,crosses_closure=False,mfe=mfe*2,mae=mae*2,terminal_delta=delta*2,mfe_atr=mfe,mae_atr=mae,terminal_delta_atr=delta,
                favorable=delta>0,neutral=delta==0,adverse=delta<0,mfe_gt_mae=mfe>mae,mfe_mae_tie=mfe==mae))
    return pd.DataFrame(rows)


def save_table(stage,name,frame):
    p=stage/"tables"/name;p.parent.mkdir(parents=True,exist_ok=True);frame.to_csv(p,index=False,float_format="%.17g",na_rep="")


def saved_fixture(stage):
    cfg=config();cards=[];nominees=[];assessments=[];all_paths={p:[] for p in ("validation","final","recent")};final_cards=[]
    for j,(p,i,b) in enumerate(CELLS):
        fixed=gate_id("absolute",cfg["minimum_width_points"][p]);chosen=fixed if j%4==0 else "atr_0p5"
        for g in gate_grid(cfg,p):
            out=synthetic_paths(p,i,b,g,"development",shift=(g["threshold"]*.02 if g["family"]=="absolute" else g["threshold"]*.3)-.04)
            payload=dict(product=p,interval_minutes=i,touch_mode=b,gate=g)
            cards.append(summaries(out,payload,"development",HORIZONS))
        nominees.append(dict(product=p,interval_minutes=i,touch_mode=b,phase="development",fixed_gate_id=fixed,nominee_gate_id=chosen,selected_gate_id=chosen,
            eligible_candidates=0 if chosen==fixed else 2,highest_eligible_score=np.nan if chosen==fixed else .2,tied_to_highest_count=0 if chosen==fixed else 1,
            nomination_status="no_eligible_improvement" if chosen==fixed else "eligible_nominee",fallback=chosen==fixed,selection_score=np.nan if chosen==fixed else .2,
            selection_improvement=np.nan if chosen==fixed else .1,selected_gate_family="absolute" if chosen==fixed else "atr",selected_gate_threshold=cfg["minimum_width_points"][p] if chosen==fixed else .5))
        assessments.append(dict(product=p,interval_minutes=i,touch_mode=b,gate_id=chosen,eligible=chosen!=fixed,failed_guards="improvement" if chosen==fixed else "",overall_improvement=0. if chosen==fixed else .1))
        for phase in all_paths:
            for gid in set((chosen,fixed)):
                gate=next(g for g in gate_grid(cfg,p) if g["gate_id"]==gid)
                shift=0. if gid==fixed else ((j%3)-1)*.09
                out=synthetic_paths(p,i,b,gate,phase,shift=shift);all_paths[phase].append(out)
                if phase=="final":final_cards.append(summaries(out,dict(product=p,interval_minutes=i,touch_mode=b,gate=gate),phase,HORIZONS))
    nominees=pd.DataFrame(nominees);decisions=validation_decisions(pd.DataFrame(assessments),nominees,cfg)
    for frame in (nominees,decisions):
        frame["row_id"]=[f"choice|{p}|{i}|{b}" for p,i,b in frame[["product","interval_minutes","touch_mode"]].itertuples(index=False,name=None)]
    grid=grid_comparisons(pd.concat(cards,ignore_index=True),cfg)
    save_table(stage,TABLES["grid"],grid);save_table(stage,TABLES["neighbors"],neighborhoods(grid));save_table(stage,TABLES["nominees"],nominees);save_table(stage,TABLES["decisions"],decisions)
    save_table(stage,TABLES["folds"],pd.DataFrame(dict(row_id=["synthetic-preparation-only"],record_kind=["synthetic_fixture"])))
    for phase,frames in all_paths.items():
        effects,_=period_effects(pd.concat(frames,ignore_index=True),nominees if phase=="validation" else decisions,cfg,phase)
        save_table(stage,TABLES[phase],effects)
    save_table(stage,TABLES["horizons"],pd.concat(final_cards,ignore_index=True))
    coverage=[]
    for p in ("ES","GC","NQ"):
        for i in (3,5):
            for y in range(2017,2027):
                share=.2+.05*(y-2017)
                coverage.append(dict(row_id=f"coverage|{p}|{i}|{y}",product=p,interval_minutes=i,year=y,scope="causal_warmup_input_only" if y==2017 else "input_only",
                    scheduled_slots=10000,usable_slots=9000,calendar_uncertified_slots=400,feature_ready_slots=int(10000*share),mapped_ready_slots=int(10000*share),atr_valid_slots=int(10000*share),
                    ready_share=share,usable_share=.9,unknown_signal_slots=int(10000*(1-share)),contributing_sessions=200,ready_sessions=int(200*share),
                    first_timestamp=f"{y}-01-02T14:00:00+00:00",last_available_at=f"{y}-09-18T21:00:00+00:00",coverage_complete=False))
    save_table(stage,TABLES["coverage"],pd.DataFrame(coverage))
    return cfg


class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        persistent=os.environ.get("STUDY21_STAGE3_REPORT_FIXTURE")
        cls.temp=None if persistent else tempfile.TemporaryDirectory()
        cls.stage=Path(persistent if persistent else cls.temp.name).resolve()
        if cls.stage.exists() and any(cls.stage.iterdir()):raise ValueError("synthetic report fixture destination must be new")
        cls.stage.mkdir(parents=True,exist_ok=True)
        retained=os.environ.get("STUDY21_STAGE3_REPORT_TABLES")
        if retained:
            (cls.stage/'tables').mkdir()
            for path in Path(retained).glob('*.csv'):shutil.copyfile(path,cls.stage/'tables'/path.name)
        else:saved_fixture(cls.stage)
        cls.result=render_bundle(cls.stage,"20261011T023748Z_s3_fixture")

    @classmethod
    def tearDownClass(cls):
        if cls.temp:cls.temp.cleanup()

    def test_complete_saved_render_and_exact_transfer(self):
        self.assertEqual(self.result["figures"],6);self.assertEqual(self.result["claims"],12);self.assertEqual(self.result["downloads"],4)
        review=verify_publication(self.stage)
        self.assertEqual(review["status"],"passed");self.assertGreater(review["cells"],1000)
        self.assertLess((self.stage/"publication.json").stat().st_size,96*1024)
        self.assertTrue(all(not Path(pin['path']).is_absolute() for pin in review['records']))
        self.assertTrue({'publication.json','source-bindings.json','report.md','report.html','advice.md'}<=set(pin['path'] for pin in review['records']))

    def test_private_real_publisher_dryrun(self):
        workspace=Path(__file__).resolve().parents[3]
        result=subprocess.run([shutil.which("node"),str(workspace/"apps/narada/scripts/publish.mjs"),"--report",str(self.stage/"publication.json"),"--dry-run"],cwd=workspace/"apps/narada",text=True,capture_output=True)
        (self.stage/"publisher-dryrun.log").write_text(result.stdout+result.stderr)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_mutated_public_cell_and_download_are_rejected(self):
        path=self.stage/"publication.json";original=path.read_bytes();bindingpath=self.stage/"source-bindings.json";originalbinding=bindingpath.read_bytes()
        try:
            pub=json.loads(original);section=next(s for s in pub["sections"] if s["id"]=="primary-final");section["rows"][0]["estimate"]=9.
            path.write_text(json.dumps(pub));bindings=json.loads(originalbinding)
            from src.stage3_reconcile import sha256
            bindings["publication_sha256"]=sha256(path);bindingpath.write_text(json.dumps(bindings))
            with self.assertRaisesRegex(ValueError,"public cell"):verify_publication(self.stage)
        finally:path.write_bytes(original);bindingpath.write_bytes(originalbinding)

    def test_false_aggregate_and_claim_wording_are_rejected(self):
        from src.stage3_reconcile import sha256
        path=self.stage/'publication.json';bindingpath=self.stage/'source-bindings.json';original=path.read_bytes();originalbinding=bindingpath.read_bytes()
        for mutation in ('aggregate','claim','selector','figure_row_id','download_selector'):
            try:
                pub=json.loads(original);bindings=json.loads(originalbinding)
                if mutation=='aggregate':pub['summary']='All twelve gateways establish positive profitability.'
                elif mutation=='claim':
                    old=bindings['claims'][0]['text'];bindings['claims'][0]['text']='A false effect claim.'
                    next(s for s in pub['sections'] if s['id']=='findings')['body']=next(s for s in pub['sections'] if s['id']=='findings')['body'].replace(old,'A false effect claim.')
                elif mutation=='selector':bindings['cells'][-1]['source_rows']=bindings['cells'][-1]['source_rows'][:-1]
                elif mutation=='figure_row_id':bindings['figures'][0]['sources'][0]['row_ids'][0]='corrupted'
                else:bindings['downloads'][2]['source_rows']=bindings['downloads'][2]['source_rows'][:-1]
                path.write_text(json.dumps(pub));bindings['publication_sha256']=sha256(path);bindingpath.write_text(json.dumps(bindings))
                with self.assertRaises(ValueError,msg=mutation):verify_publication(self.stage)
            finally:path.write_bytes(original);bindingpath.write_bytes(originalbinding)

    def test_frozen_final_assessment_values_classification_and_pins(self):
        from src.stage3_reconcile import record,read_csv,reconcile_final_assessment
        files=[self.stage/'config.json',self.stage/'provenance/independent-final.json',self.stage/'provenance/final-assessment.json']
        try:
            files[0].write_text(json.dumps(config()))
            files[1].write_text(json.dumps(dict(status='passed',phase='final')))
            _,rows=read_csv(self.stage/'tables/S3-T14_final_effects.csv')
            bindings=json.loads((self.stage/'source-bindings.json').read_text());primary=[rows[i-1] for i in bindings['aggregate_claim']['source_rows']]
            classifications=dict(includes_zero=6,above_zero=3,below_zero=3,undefined=0)
            saved=dict(status='frozen_final_assessment_before_recent',period='final',classification=classifications,primary_rows=primary,conclusion=bindings['aggregate_claim']['text'],family=config()['primary_comparison_family'],records=[])
            for relative in ('tables/S3-T14_final_effects.csv','provenance/independent-final.json'):saved['records'].append(record(self.stage/relative)|dict(path=relative))
            files[2].write_text(json.dumps(saved));result=reconcile_final_assessment(self.stage);self.assertEqual(result['classification'],classifications)
            transfer=verify_publication(self.stage);self.assertIn('provenance/final-assessment.json',{p['path'] for p in transfer['records']})
            saved['classification']['above_zero']=12;files[2].write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError,'values/classification/conclusion'):reconcile_final_assessment(self.stage)
        finally:
            for path in files:
                if path.exists():path.unlink()

    def test_render_overwrite_refused(self):
        with self.assertRaisesRegex(ValueError,"overwrite refused"):render_bundle(self.stage,"20261011T023748Z_s3_fixture")


if __name__=="__main__":unittest.main()

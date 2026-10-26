"""Synthetic empirical cloud geometry/source fixtures, not historical data."""
import ast
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from phase3_publish_web import Draft,ReportSpec,SavedInputs
import phase3_cloud_figures as render

SCRIPT=Path(__file__).resolve().parents[1]/'phase3_verify_publication.py'
spec=importlib.util.spec_from_file_location('independent_cloud_check',SCRIPT)
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)


def clock(minute):return f'2020-01-01T09:{minute:02d}:00+00:00'


class Phase3CloudFigureTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.stage=Path(self.tmp.name);(self.stage/'tables').mkdir()
        self.case=dict(id='a20-add-win-long',episode_id='synthetic-episode',contract='SYNTHETIC',policy='A20',mode='diagnostic_1plus1',leg='add',kind='add_win',direction=1,parent_entry=clock(5),parent_fill_upper=clock(6),parent_entry_price=4000,parent_initial_stop=3960,parent_reset_stop=3990,parent_reset_at=clock(9),parent_exit=clock(30),parent_exit_price=4008,signal_at=clock(15),contact_open=clock(10),frozen_level=4001,frozen_level_available_at=clock(10),liquidation_net=125,parent_open_at_signal=True,policy_net_dollars=200,action_at=clock(16),action_price=4002,window_start=clock(0),window_end=clock(35),range_high=4008,midpoint=4000,range_low=3992,legs=[dict(leg='original',entry_time=clock(5),entry_price=4000,initial_stop=3960,reset_stop=3990,reset_stop_active_at=clock(9),exit_time=clock(30),exit_price=4008),dict(leg='add',entry_time=clock(16),entry_price=4002,initial_stop=3962,reset_stop=4000,reset_stop_active_at=clock(20),exit_time=clock(30),exit_price=4008,risk_initial_dollars=4000,quantity=1)])
        self.selection=dict(schema_version='study23.phase3-balanced-examples/v1',run_id='synthetic',cases=[self.case],absent_cases=[])
        (self.stage/'example-selection.json').write_text(json.dumps(self.selection))
        self.minutes=[dict(case_id=self.case['id'],episode_id=self.case['episode_id'],contract='SYNTHETIC',timestamp=clock(i),available_at=clock(i+1),open=str(4000+i*.2),high=str(4001+i*.2),low=str(3999+i*.2),close=str(4000+i*.2),usable='True') for i in range(35)]
        self.cloud=[dict(case_id=self.case['id'],episode_id=self.case['episode_id'],contract='SYNTHETIC',timestamp=clock(i-5),available_at=clock(i),ema20='' if i==20 else str(4000+i*.1),ema50='' if i==20 else str(3998+i*.1),usable='False' if i==20 else 'True',feature_valid='False' if i==20 else 'True') for i in range(5,36,5)]
        self.write('selected-example-minutes',self.minutes);self.write('selected-example-cloud',self.cloud)

    def write(self,name,rows):
        with (self.stage/'tables'/f'{name}.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    def draft(self):return Draft(SavedInputs(self.stage),'synthetic',ReportSpec('ema20-support','summary'))

    def projection(self,d):
        root=self.stage/'projection';root.mkdir(exist_ok=True)
        for name,data in d.files.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        mapping=dict(schema_version='study23.phase3-web-source-cells/v1',source_row_base=0,source_artifacts=list(d.sources.values()))
        return check.Projection(self.stage,root,mapping)

    def test_saved_cloud_geometry_markers_levels_own_risk_and_clock_labels_match_independently(self):
        d=self.draft();sections=[];render.add_cloud_examples(d,sections)
        self.assertEqual(len(sections),1);self.assertEqual(len(d.figures),1)
        record=d.figures[0];tree=ET.fromstring(d.files[record['svg_path']])
        self.assertGreater(check.verify_cloud_path(record,tree,self.projection(d)),0)
        panel=record['plot_encoding']['panels'][0]
        self.assertEqual(panel['mode'],'diagnostic_1plus1')
        self.assertEqual(panel['series'][1]['segments'],[[0,1,2],[4,5,6]])
        self.assertEqual({x['id'] for x in panel['markers']},{'original-fill','actual-policy-action','parent-comparator-exit'})
        self.assertTrue({'range-H','range-M','range-L','frozen-contact','parent-initial-stop','parent-reset-stop','add-initial-stop','add-reset-stop'}<={x['id'] for x in panel['levels']})
        self.assertTrue({'own-leg-risk','own-leg-quantity','observed-start','observed-end','signal-clock','action-clock','original-fill-clock','parent-open'}<={x['id'] for x in panel['annotations']})

    def test_no_best_pnl_reselection_and_absent_case_does_not_create_a_marker(self):
        self.case.update(kind='rejected_support',action_at=None,action_price=None,legs=[self.case['legs'][0]])
        self.selection['absent_cases']=[dict(id='a20-add-loss-short',policy='A20',mode='diagnostic_1plus1',kind='add_loss',direction=-1,status='no_qualifying_saved_case')]
        (self.stage/'example-selection.json').write_text(json.dumps(self.selection))
        d=self.draft();sections=[];render.add_cloud_examples(d,sections)
        panel=d.figures[0]['plot_encoding']['panels'][0]
        self.assertNotIn('actual-policy-action',{m['id'] for m in panel['markers']})
        self.assertTrue(any(a['id']=='action-clock' and a['source_binding']['value_type']=='null' for a in panel['annotations']))
        absent=next(s for s in sections if s['kind']=='table')
        self.assertEqual(absent['rows'][0]['status'],'no_qualifying_saved_case')
        check.verify_cloud_path(d.figures[0],ET.fromstring(d.files[d.figures[0]['svg_path']]),self.projection(d))

    def test_future_prior_level_and_wrong_contract_are_not_rendered_as_valid_examples(self):
        self.case['frozen_level_available_at']=clock(11)
        (self.stage/'example-selection.json').write_text(json.dumps(self.selection))
        d=self.draft();render.add_cloud_examples(d,[])
        with self.assertRaisesRegex(ValueError,'causal available'):check.verify_cloud_path(d.figures[0],ET.fromstring(d.files[d.figures[0]['svg_path']]),self.projection(d))
        self.cloud[0]['contract']='OTHER';self.write('selected-example-cloud',self.cloud)
        with self.assertRaisesRegex(ValueError,'contract/episode mismatch'):render.add_cloud_examples(self.draft(),[])

    def test_only_requested_summary_groups_consume_example_sources(self):
        d=Draft(SavedInputs(self.stage),'synthetic',ReportSpec('ema20-support','year'));render.add_cloud_examples(d,[])
        self.assertFalse(d.sources)
        d=Draft(SavedInputs(self.stage),'synthetic',ReportSpec('entry-gates','summary'));render.add_cloud_examples(d,[])
        self.assertFalse(d.sources)

    def test_renderer_does_not_import_research_or_independent_verifier(self):
        modules=[n.module for n in ast.walk(ast.parse(Path(render.__file__).read_text())) if isinstance(n,ast.ImportFrom)]
        self.assertFalse(any('engine' in name or 'metrics' in name or 'verify' in name or 'phase3_publish' in name for name in modules))


if __name__=='__main__':unittest.main()

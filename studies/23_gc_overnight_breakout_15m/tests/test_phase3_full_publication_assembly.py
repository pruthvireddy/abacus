"""Full nineteen-report contract fixture, with complete frozen-schema rosters.

All CSV/JSON values below are synthetic. This tests the complete assembly and
bounds; it neither imports numerical producers nor reads historical outcomes.
"""
import copy
import csv
import json
from pathlib import Path
import unittest
import test_phase3_report_supplements as fixtures
import test_phase3_cloud_figures as cloud_fixture
from phase3_publish_web import Draft,ReportSpec,SavedInputs,assemble,report_specs

BUCKETS={
 'availability':('known','unknown'),'ordering':('aligned','opposed','neutral'),
 'price_position':('above','inside','below'),'slopes':('both_aligned','both_opposed','mixed_or_flat','unknown'),
 'width_atr':('below_0','[0,0.25)','[0.25,0.5)','[0.5,1)','[1,2)','>=2','unknown'),
 'distance_atr':('below_0','[0,0.5)','[0.5,1)','[1,2)','>=2','unknown'),
 'aligned_duration':('below_1','[1,4)','[4,13)','[13,37)','>=37','left_censored','unknown'),
 'width_change':('expanding','contracting','equal','unknown'),
 **{f'confluence_ema{e}_{level}':('yes','no','unknown') for e in (20,50) for level in ('H','L','M')},
}


class FullPhase3AssemblyTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.Phase3SupplementTests(methodName='test_module_never_imports_any_numerical_producer');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture=f;self.stage=f.stage
        (self.stage/'config.json').write_text(json.dumps({'fixture':'synthetic only'}))
        candidates=[dict(policy=p,validation_complete_pairs=0,mean_difference=None,adjusted_low=None,completed_trades=0,financed_add_fills=0,qualifies=False) for p in fixtures.supplement.CORE]
        (self.stage/'selection.json').write_text(json.dumps(dict(candidates=candidates,selected_gate=None,selected_exit=None,selected_adds=[],combined_policy=None)))
        (self.stage/'execution-completion.json').write_text(json.dumps(dict(phase3='computed',finished_at='2026-10-13T23:00:00Z',scope='Synthetic contract fixture only')))
        self.extend('paired',['individual_pairs','individual_mean_difference','difference_low','difference_high','adjusted_low','adjusted_high'])
        self.extend('trade-cohorts',['payoff','gross_points','net_points','cost_dollars'])
        riskkeys=['policy','mode','anchor','year','session','side','episodes','known_outcomes','unknown_outcomes','net_dollars','original_fills','add_fills','original_quantity_skips','add_quantity_skips','cancellations','unused_reserve_dollars','mean_unused_reserve_dollars','reserve_allocation_denominator','planned_risk_overshoot_episodes','peak_notional','episode_mtm_drawdown_dollars','financing_enforced','signals','add_attempts','support_rejections','unknown_support_abstentions']
        groups=[('BASE',m) for m in ('parent_1','parent_2','full_parent','half_parent')]+[(p,m) for p in ('A20','A50') for m in ('financed_overlay','diagnostic_1plus1')]
        f.write('risk',[fixtures.row(riskkeys,policy=p,mode=m,anchor='original_actual_entry',**c) for p,m in groups for c in fixtures.cohorts()])
        profilekeys=['anchor','feature',*fixtures.supplement.PROFILE,'conditional_population','not_calibrated_probability','mean_parent_mfe_points','mean_parent_mae_points','mean_parent_holding_minutes']
        anchors=('original_order_decision','original_entry','eligible_open_position_landmark','phase2_saved_event_context_midpoint_touch','phase2_saved_event_context_protected_low_tick_breach','phase2_saved_event_context_protected_high_close_break')
        f.write('profiles',[fixtures.row(profilekeys,anchor=a,feature=feature,bucket=b,**c) for a in anchors for feature,buckets in BUCKETS.items() for b in buckets for c in fixtures.cohorts()])
        equitykeys=['policy','mode','leg','anchor','trade_id','exit_time','cumulative_net_dollars','drawdown_dollars']
        # No financed closed path: realistic zero-execution presentation branch.
        f.write('equity',[dict(policy=p,mode=m,leg='combined',anchor='actual_leg_fill',trade_id='synthetic-'+p,exit_time='2020-01-01T17:00:00+00:00',cumulative_net_dollars='10',drawdown_dollars='-5') for p,m in [('G1','standardized'),('G2','standardized'),('X1','standardized'),('X2','standardized'),('T50','standardized'),('A20','diagnostic_1plus1'),('A50','diagnostic_1plus1')]])
        keys=['policy','anchor','year','session','side','episodes','complete_pairs','missing_pairs','mean_difference','improved','deteriorated','parent_losers','losses_reduced','loss_dollars_saved','parent_winners','winners_cut_short','profit_surrendered_dollars','mean_time_saved_minutes','mean_post_exit_favorable_points']
        f.write('exit-tradeoffs',[fixtures.row(keys,policy=p,anchor='original_actual_entry',**c) for p in ('X1','X2','T50') for c in fixtures.cohorts()])
        self.examples()

    def extend(self,name,keys):
        path=self.stage/'tables'/f'{name}.csv'
        with path.open(newline='') as stream:rows=list(csv.DictReader(stream))
        for r in rows:
            for key in keys:
                if key not in r:r[key]='' if any(w in key for w in ('difference','payoff')) else '0'
        self.fixture.write(name,rows)

    def examples(self):
        f=cloud_fixture.Phase3CloudFigureTests(methodName='test_only_requested_summary_groups_consume_example_sources');f.setUp()
        try:
            cases=[];absent=[];minutes=[];cloud=[]
            for p,kinds in {'A20':('add_win','add_loss','rejected_support'),'A50':('add_win','add_loss','rejected_support'),'X1':('loss_saved','winner_cut_short'),'X2':('loss_saved','winner_cut_short')}.items():
                # Both an empirical figure and an absent-category table per policy.
                for kind in kinds:
                    for direction in (1,-1):
                        id=p.lower()+'-'+kind.replace('_','-')+('-long' if direction==1 else '-short')
                        mode='diagnostic_1plus1' if p.startswith('A') else 'standardized'
                        if kind==kinds[-1] and direction==-1:
                            absent.append(dict(id=id,policy=p,mode=mode,kind=kind,direction=direction,status='no_qualifying_saved_case'));continue
                        c=copy.deepcopy(f.case);c.update(id=id,episode_id='synthetic-'+id,policy=p,mode=mode,leg='add' if p.startswith('A') else 'original',kind=kind,direction=direction)
                        if not p.startswith('A') or kind=='rejected_support':c['legs']=[c['legs'][0]]
                        if kind=='rejected_support':c.update(action_at=None,action_price=None)
                        if p=='X1':c.update(parent_entry=cloud_fixture.clock(0),parent_fill_upper=cloud_fixture.clock(1),frozen_level_contact_open=cloud_fixture.clock(5),frozen_level_available_at=cloud_fixture.clock(5))
                        if p=='X2':c['frozen_level']=None
                        cases.append(c)
                        for original,target in ((f.minutes,minutes),(f.cloud,cloud)):
                            for r in original:
                                item=dict(r,case_id=id,episode_id=c['episode_id']);target.append(item)
            selection=dict(schema_version='study23.phase3-balanced-examples/v1',run_id='synthetic',cases=cases,absent_cases=absent,source_selection='Synthetic preselected fixture; no historical policy scoring')
            (self.stage/'example-selection.json').write_text(json.dumps(selection))
            self.fixture.write('selected-example-minutes',minutes);self.fixture.write('selected-example-cloud',cloud)
        finally:f.doCleanups()

    def test_complete_nineteen_reports_fit_every_existing_bound_and_distinct_source_anchor(self):
        self.sizes=[]
        for spec in report_specs():
            d=Draft(SavedInputs(self.stage),'synthetic',spec);report=assemble(d)
            raw=json.dumps(report,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
            self.assertLessEqual(len(raw),2*1024*1024,(spec.group,spec.view,len(raw)))
            self.assertLessEqual(len(report['sections']),30,(spec.group,spec.view))
            self.assertLessEqual(len(d.figures),12);self.assertLessEqual(len(d.downloads),4)
            self.assertEqual(len({s['id'] for s in report['sections']}),len(report['sections']))
            self.assertEqual(report['sections'][-1]['id'],'uncertainty')
            for table in [s for s in report['sections'] if s['kind']=='table']:
                self.assertLessEqual(len(table['columns']),12);self.assertLessEqual(len(table['rows']),1500 if table.get('rowFilters') else 100)
                self.assertLessEqual(len(table.get('rowFilters',[])),3)
            self.assertLessEqual(sum(len(d.files[r['path']]) for r in d.downloads),8*1024*1024)
            self.sizes.append(dict(group=spec.group,view=spec.view,bytes=len(raw),sections=len(report['sections']),figures=len(d.figures),downloads=len(d.downloads)))
        self.assertEqual(len(self.sizes),19)

    def test_financed_no_path_stays_absent_and_diagnostic_paths_and_exact_controls_are_visible(self):
        for group in ('ema20-support','ema50-support'):
            d=Draft(SavedInputs(self.stage),'synthetic',ReportSpec(group,'summary'));report=assemble(d)
            figure_ids={s['id'] for s in report['sections'] if s['kind']=='figure'}
            p='a20' if group=='ema20-support' else 'a50'
            self.assertNotIn(p+'-equity',figure_ids)
            diagnostic=[r for r in d.figures if d.sources[r['source_artifact']].get('selectors',{}).get('mode')=='diagnostic_1plus1']
            self.assertEqual({r['plot_encoding']['value_column'] for r in diagnostic},{'cumulative_net_dollars','drawdown_dollars'})
            control=next(s for s in report['sections'] if s['id']=='supp-'+p+'-exposure-controls')
            self.assertEqual({r['c3'] for r in control['rows']},{'BASE:parent_1','BASE:parent_2'})
            self.assertIn('Common three-path',next(c['label'] for c in control['columns'] if c['key']=='c5'))


if __name__=='__main__':unittest.main()

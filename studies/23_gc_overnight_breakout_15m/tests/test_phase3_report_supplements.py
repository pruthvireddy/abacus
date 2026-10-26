"""Saved-cell presentation fixtures; no historical outcomes or producer imports."""
import ast
import csv
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from phase3_publish_web import Draft,ReportSpec,SavedInputs
import phase3_report_supplements as supplement

SCRIPT=Path(__file__).resolve().parents[1]/'phase3_verify_publication.py'
spec=importlib.util.spec_from_file_location('independent_supplement_check',SCRIPT)
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
YEARS=('all',*(str(y) for y in range(2018,2027)))
SIDES=('combined','long','short')
SESSIONS=('all',*supplement.SESSIONS)


def cohorts():
    return [dict(year=y,session=s,side=d) for y in YEARS for s in SESSIONS for d in SIDES]


def row(keys,**saved):
    result={k:'False' if k in supplement.FLAGS else 'unknown' if k in supplement.TEXT else '' if k in supplement.RATES or 'dollars' in k or 'difference' in k or 'mean_' in k else '0' for k in keys}
    result.update(saved);return result


class Phase3SupplementTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.stage=Path(self.tmp.name);(self.stage/'tables').mkdir()
        (self.stage/'protocol.md').write_text('Synthetic frozen method only. No historical results.')
        pairedkeys=list(dict.fromkeys(['policy','mode','control','anchor',*supplement.PARTICIPATION,*supplement.DISPOSITIONS,'support_rejections',*supplement.SCENARIOS]))
        self.write('paired',[row(pairedkeys,policy=p,mode='financed_overlay' if p.startswith('A') else 'standardized',control='BASE:half_parent' if p.startswith('A') else 'BASE:parent_1',anchor='original_actual_entry',**c) for p in supplement.CORE for c in cohorts()])
        floatingkeys=['policy','mode','anchor',*supplement.FLOATING,'within_year_path']
        groups=[(p,'financed_overlay' if p.startswith('A') else 'standardized') for p in (*supplement.CORE,'T50')]+[('BASE',m) for m in ('parent_1','parent_2','full_parent','half_parent')]
        self.write('floating',[row(floatingkeys,policy=p,mode=m,anchor='original_actual_entry',**c) for p,m in groups for c in cohorts()])
        riskkeys=['policy','mode','anchor','year','session','side','episodes','signals','add_attempts','support_rejections','unknown_support_abstentions','add_quantity_skips','cancellations','known_outcomes','unknown_outcomes']
        self.write('risk',[row(riskkeys,policy=p,mode='financed_overlay',anchor='original_actual_entry',**c) for p in ('A20','A50') for c in cohorts()])
        keys=['policy','mode','control','anchor','year','session','side','episodes','complete_pairs','missing_pairs','individual_pairs','alternative_net_dollars','control_net_dollars','total_difference','mean_difference','individual_mean_difference','larger_exposure','not_equal_risk']
        self.write('exposure-controls',[row(keys,policy=p,mode='diagnostic_1plus1',control=control,anchor='original_actual_entry',larger_exposure='True',not_equal_risk='True',**c) for p in ('A20','A50') for control in ('BASE:parent_1','BASE:parent_2') for c in cohorts()])
        keys=list(dict.fromkeys(['policy','mode','leg','anchor','year','session','side','fills','completed','censored','net_dollars','win_rate','expectancy_dollars','profit_factor','closed_drawdown_dollars','distinct_episodes','wins','losses','breakevens','net_r','r_denominator','mfe_points','mae_points','holding_minutes','gross_dollars']))
        groups=[(p,m) for p in (*supplement.CORE,'T50') for m in (('financed_overlay','diagnostic_1plus1') if p.startswith('A') else ('standardized',))]
        self.write('trade-cohorts',[row(keys,policy=p,mode=m,leg=leg,anchor='actual_leg_fill',**c) for p,m in groups for leg in ('combined','add') for c in cohorts()])
        self.write('scenarios',[row([*supplement.SCENARIOS,'anchor'],policy=p,scenario=s,side=d,anchor='original_actual_entry') for p in supplement.CORE for s in ('primary-one-tick','high-first') for d in SIDES])
        self.write('interval-sensitivities',[row([*supplement.INTERVALS,'anchor'],policy=p,period=period,side=d,block_weeks=str(w),anchor='original_actual_entry') for p in supplement.CORE for period in ('development','validation','later','replication') for d in SIDES for w in (1,4,8)])
        profilekeys=['anchor','feature',*supplement.PROFILE,'conditional_population','not_calibrated_probability','mean_parent_mfe_points','mean_parent_mae_points','mean_parent_holding_minutes']
        features=('availability','ordering','price_position','slopes','width_atr','distance_atr','width_change',*(f'confluence_ema{e}_{level}' for e in (20,50) for level in ('H','L','M')))
        anchors=('original_order_decision','original_entry','eligible_open_position_landmark','phase2_saved_event_context_midpoint_touch','phase2_saved_event_context_protected_low_tick_breach','phase2_saved_event_context_protected_high_close_break')
        self.write('profiles',[row(profilekeys,anchor=a,feature=f,bucket='unknown',**c) for a in anchors for f in features for c in cohorts()])
        contactkeys=['ema','event','anchor',*supplement.CONTACT,'mean_recovery_minutes','recovery_timing_denominator','observed_recovery_timing_unknown','eligible_open_landmarks','eligible_open_episodes']
        self.write('contacts',[row(contactkeys,ema=str(e),event=event,contact_group=g,anchor='EMA_decision_event',**c) for e in (20,50) for event in supplement.CONTACT_EVENTS for g in ('all','first','second','third_or_more','unknown') for c in cohorts()])
        keys=['ema','level','confluence_state','event','year','session','side','anchor','contacts','distinct_episodes','known_events','known_none','unknown','known_denominator','rate','lower_bound','upper_bound','conditional_population']
        self.write('confluence',[row(keys,ema=str(e),level=level,confluence_state=state,event=event,anchor='EMA_decision_event',**c) for e in (20,50) for level in ('H','L','M') for state in ('yes','no','unknown') for event in supplement.CONTACT_EVENTS for c in cohorts()])
        self.write('forward',[row(['ema','horizon_minutes','anchor',*supplement.FORWARD],ema=str(e),horizon_minutes=str(h),contact_group=g,anchor='EMA_decision_event',**c) for e in (20,50) for h in (5,15,30,60) for g in ('all','first','second','third_or_more','unknown') for c in cohorts()])
        transitionkeys=['policy','mode','anchor',*supplement.TRANSITIONS]
        self.write('transitions',[row(transitionkeys,policy=p,mode=m,anchor='EMA_event_year',year=y,side=d,original_session=o,event_session=e,add_session=a) for p in ('A20','A50') for m in ('financed_overlay','diagnostic_1plus1') for y in YEARS for d in SIDES for o in supplement.SESSIONS for e in supplement.SESSIONS for a in (*supplement.SESSIONS,'unfilled')])

    def write(self,name,rows):
        with (self.stage/'tables'/f'{name}.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

    def draft(self,group,view):
        d=Draft(SavedInputs(self.stage),'synthetic',ReportSpec(group,view));d.copy_text('protocol.md');return d

    def verify_tables(self,d,sections):
        pub=self.stage/'projection';pub.mkdir(exist_ok=True)
        for name,data in d.files.items():
            p=pub/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        mapping=dict(schema_version='study23.phase3-web-source-cells/v1',source_row_base=0,source_artifacts=list(d.sources.values()),bindings=d.bindings,table_assertions=d.table_assertions)
        projection=check.Projection(self.stage,pub,mapping)
        check.display_cells(dict(sections=sections),mapping,projection)
        check.table_assertions(dict(sections=sections),mapping,projection)
        return mapping

    def test_all_planned_views_obey_existing_section_table_filter_and_csv_bounds(self):
        for group in ('entry-gates','ema20-support','ema50-support','earlier-exits','other-cloud-uses','trend-context','methods-risk'):
            for view in (('summary',) if group=='methods-risk' else ('summary','year','sessions')):
                d=self.draft(group,view);sections=[];supplement.add_supplements(d,sections)
                self.assertLessEqual(len(sections),29);self.assertLessEqual(len(d.downloads),4)
                self.assertEqual(len({s['id'] for s in sections}),len(sections))
                for table in [s for s in sections if s['kind']=='table']:
                    self.assertLessEqual(len(table['rows']),1500);self.assertLessEqual(len(table['columns']),12);self.assertLessEqual(len(table.get('rowFilters',[])),3)
                for download in d.download_entries:
                    self.assertLessEqual(download['rowCount'],15000);self.assertLessEqual(len(download['columns']),24)

    def test_original_cohort_counts_nulls_and_rejections_have_exact_source_cells(self):
        d=self.draft('entry-gates','summary');sections=[];supplement.add_supplements(d,sections)
        mapping=self.verify_tables(d,sections)
        self.assertIn('rejections',{b['original_source_column'] for b in mapping['bindings']})
        self.assertIn('unknown_feature_slots',{b['original_source_column'] for b in mapping['bindings']})
        self.assertTrue(all(b['original_source_column']==b['source_column'] for b in mapping['bindings']))
        self.assertTrue(any(b['value_type']=='null' for b in mapping['bindings']))
        self.assertEqual(set(d.sources['tables/supp-g1-participation.csv']['selected_source_rows']),set(range(150)))

    def test_add_only_and_event_transitions_have_separate_labels_and_complete_600_row_partitions(self):
        d=self.draft('ema20-support','sessions');sections=[];supplement.add_supplements(d,sections)
        self.verify_tables(d,sections)
        addtables=[s for s in sections if 'add-only' in s['id']]
        self.assertEqual(len(addtables),2)
        self.assertTrue(all('Actual add-entry' in s['rowFilters'][0]['label'] for s in addtables))
        transitions=[s for s in sections if '-transition-' in s['id']]
        self.assertEqual(len(transitions),4);self.assertEqual([len(s['rows']) for s in transitions],[600]*4)
        self.assertTrue(all(s['rowFilters'][0]['label']=='EMA event year' for s in transitions))
        self.assertTrue(all(s['rowFilters'][1]['label']=='EMA signal/event session' for s in transitions))
        self.assertEqual({r['c4'] for s in transitions for r in s['rows']},{*supplement.SESSIONS,'unfilled'})

    def test_other_price_paths_cover_all_four_exact_horizons_repeat_groups_and_time_unknowns(self):
        d=self.draft('other-cloud-uses','year');sections=[];supplement.add_supplements(d,sections)
        self.verify_tables(d,[s for s in sections if s['kind']!='figure'])
        forward=[s for s in d.sources.values() if s['original_stage_source_path']=='tables/forward.csv']
        self.assertEqual({s['selectors'].get('horizon_minutes') for s in forward if 'horizon_minutes' in s['selectors']},{'5','15','30','60'})
        sources=[s for s in d.sources.values() if 'recovery-timing' in s['path']]
        self.assertEqual(len(sources),2)
        self.assertTrue(all('observed_recovery_timing_unknown' in s['columns'] for s in sources))
        self.assertTrue(all(len(d.copied_table(s['path']))==150 for s in sources))
        self.assertTrue(all('session' in s['selectors'] and s['selectors']['session']=='all' for s in sources))

    def test_all_six_frozen_range_confluence_and_phase2_context_are_retained(self):
        d=self.draft('other-cloud-uses','summary');sections=[];supplement.add_supplements(d,sections)
        self.verify_tables(d,sections)
        self.assertEqual({s['selectors']['feature'] for s in d.sources.values() if isinstance(s.get('selectors',{}).get('feature'),str) and s['selectors']['feature'].startswith('confluence_')},{f'confluence_ema{e}_{level}' for e in (20,50) for level in ('H','L','M')})
        d=self.draft('other-cloud-uses','sessions');sections=[];supplement.add_supplements(d,sections);self.verify_tables(d,sections)
        self.assertEqual(len(d.downloads),4)
        self.assertTrue(all({'year','session','side','anchor'}<=set(d.sources[download['source_artifact']]['columns']) for download in d.downloads))

    def test_missing_required_column_and_overflow_fail_without_a_fabricated_cell(self):
        d=self.draft('entry-gates','summary');headers,rows=d.inputs.table('tables/paired.csv')
        d.inputs.tables['tables/paired.csv']=([k for k in headers if k!='signals'],[{k:v for k,v in r.items() if k!='signals'} for r in rows])
        with self.assertRaisesRegex(ValueError,'missing frozen saved'):supplement.add_supplements(d,[])
        d=self.draft('ema20-support','sessions');sections=[dict(id=f'prior-{i}',kind='text',body='Synthetic') for i in range(25)]
        with self.assertRaisesRegex(ValueError,'leaves no room'):supplement.add_supplements(d,sections)

    def test_module_never_imports_any_numerical_producer(self):
        imports=[node.module for node in ast.walk(ast.parse(Path(supplement.__file__).read_text())) if isinstance(node,ast.ImportFrom)]
        self.assertFalse(any('metrics' in name or 'engine' in name or 'run' in name or 'verify' in name for name in imports))


if __name__=='__main__':unittest.main()

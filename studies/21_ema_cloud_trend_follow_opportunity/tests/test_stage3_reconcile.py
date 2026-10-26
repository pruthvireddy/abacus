"""Independent scientific checks against actual producer schemas and mutations."""
import copy
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from src import stage3_reconcile as c
from src import stage3_reference as ref
from src.stage3_statistics import summaries, stability, period_effects
from src.stage3_selection import fold_records, assess_candidates, select_nominees, validation_decisions
from tests.test_stage3_reference import config, roster
from tests.test_stage3_reporting import synthetic_paths


def strings(frame):return list(csv.DictReader(io.StringIO(frame.to_csv(index=False,float_format='%.17g',na_rep=''))))

def fold_paths(cfg,gate,phase,shift=0.):
    rows=[]
    for fold in cfg['development_folds' if phase=='development' else 'validation_folds']:
        template=synthetic_paths('ES',5,'fast',gate,phase,shift).loc[lambda x:x.horizon.eq(15)].iloc[0].to_dict()
        first=ref.boundary(fold['start'])+pd.Timedelta(days=2,hours=9)
        for i in range(60):
            stamp=first+pd.Timedelta(days=i);day=stamp.tz_convert(ref.NY).date()
            rows.append(template|dict(timestamp=stamp,entry_at=stamp+pd.Timedelta(minutes=5),event_id=f"{gate['gate_id']}|{fold['id']}|{i}",fold_id=fold['id'],session=day.isoformat(),week=(pd.Timestamp(day)-pd.Timedelta(days=day.weekday())).date().isoformat(),terminal_delta_atr=.1+shift,mfe_atr=1.+shift,mae_atr=1.-shift))
    return pd.DataFrame(rows)


class ReconcileTests(unittest.TestCase):
    def test_exact_discrete_boolean_and_null(self):
        c.cell('1000000',1000000,'count');c.cell('False',False,'flag');c.cell('',None,'undefined')
        for raw,value in [('1000000.00001',1000000),('0',False),('garbage',False),('',False),('0',None)]:
            with self.assertRaises(ValueError):c.cell(raw,value,'mutation')
        with self.assertRaises(ValueError):c.equal(1000000.00001,1000000,'count')
        with self.assertRaises(ValueError):c.compare_frames(pd.DataFrame(dict(k=[1],n=[1000000.00001])),pd.DataFrame(dict(k=[1],n=[1000000])),['k'])
        c.equal(1.+1e-11,1.,'floating sums')

    def test_summary_full_schema_and_column_count_mutations(self):
        gate=dict(gate_id='abs_2p4',family='absolute',threshold=2.4);out=synthetic_paths('ES',5,'fast',gate,'final')
        rows=strings(summaries(out,dict(product='ES',interval_minutes=5,touch_mode='fast',gate=gate),'final',ref.HORIZONS))
        self.assertGreater(c.reconcile_summary_rows(out,rows),100)
        damaged=copy.deepcopy(rows);damaged[0].pop('mean_mfe')
        with self.assertRaisesRegex(ValueError,'required scientific summary'):c.reconcile_summary_rows(out,damaged)
        damaged=copy.deepcopy(rows);damaged[0]['completed']='6.00000000001'
        with self.assertRaisesRegex(ValueError,'integer/discrete'):c.reconcile_summary_rows(out,damaged)

    def test_all_guards_actual_nomination_and_validation_schema(self):
        cfg=config();gates=[dict(gate_id='abs_2p4',family='absolute',threshold=2.4),dict(gate_id='atr_0p5',family='atr',threshold=.5)]
        def build(phase,shift):
            paths={g['gate_id']:fold_paths(cfg,g,phase,0 if g['family']=='absolute' else shift) for g in gates}
            folds=pd.concat([fold_records(paths[g['gate_id']],g,'ES',5,'fast',[f['id'] for f in cfg['development_folds' if phase=='development' else 'validation_folds']]) for g in gates],ignore_index=True)
            return paths,folds,assess_candidates(folds,cfg,phase=phase)
        dev,folds,assess=build('development',.2);choices=select_nominees(assess,cfg)
        c.reconcile_selection(dev,gates,cfg,strings(folds),strings(assess),strings(choices))
        bad=strings(choices);bad[0]['highest_eligible_score']='9'
        with self.assertRaisesRegex(ValueError,'highest_eligible_score'):c.reconcile_selection(dev,gates,cfg,strings(folds),strings(assess),bad)
        val,folds,assess=build('validation',-.1);decisions=validation_decisions(assess,choices,cfg)
        c.reconcile_selection(val,gates,cfg,strings(folds),strings(assess),strings(decisions),'validation','atr_0p5')
        self.assertEqual(decisions.selected_gate_id.iloc[0],'abs_2p4')
        bad=strings(decisions);bad[0]['validation_improvement']='1'
        with self.assertRaisesRegex(ValueError,'validation_improvement'):c.reconcile_selection(val,gates,cfg,strings(folds),strings(assess),bad,'validation','atr_0p5')

    def test_maximum_anchored_ties_do_not_chain(self):
        gates=[dict(gate_id=f'abs_{i}',family='absolute',threshold=i) for i in range(3)]
        scores=[1.+1.8e-12,1.+.9e-12,1.];supports=[200,300,400]
        def assessment(candidate,*args):return dict(score=scores[candidate],completed=supports[candidate],eligible=True)
        with patch.object(ref,'candidate_assessment',side_effect=assessment):selected=ref.independent_selection({g['gate_id']:i for i,g in enumerate(gates)},None,gates,config())
        self.assertEqual(selected['nominee'],'abs_1')

    def test_interval_support_exact_tails_and_metadata(self):
        cfg=config();fixed=dict(gate_id='abs_2p4',family='absolute',threshold=2.4);chosen=dict(gate_id='atr_0p5',family='atr',threshold=.5)
        f=synthetic_paths('ES',5,'fast',fixed,'final');s=synthetic_paths('ES',5,'fast',chosen,'final',.2)
        choices=pd.DataFrame([dict(product='ES',interval_minutes=5,touch_mode='fast',selected_gate_id='atr_0p5',fixed_gate_id='abs_2p4')])
        effects,_=period_effects(pd.concat([f,s],ignore_index=True),choices,cfg,'final');rows=strings(effects);pop={('ES','5','fast'):(s,f)}
        c.reconcile_contrasts(rows,pop,cfg,'final')
        for name,value in [('selected_evaluable','6.000000001'),('quantile_low','.025'),('quantile_low',format(.05/24+1e-13,'.17g')), ('seed','20261010.00001'),('selected_estimate','5'),('identity_fallback','True')]:
            damaged=copy.deepcopy(rows);next(r for r in damaged if r['interval_kind']=='bonferroni12')[name]=value
            with self.assertRaises(ValueError,msg=name):c.reconcile_contrasts(damaged,pop,cfg,'final')
        damaged=copy.deepcopy(rows);damaged[0].pop('fixed_sessions')
        with self.assertRaisesRegex(ValueError,'complete contrast/support'):c.reconcile_contrasts(damaged,pop,cfg,'final')

    def test_calendar_and_common_input_volatility_empty_bins(self):
        cfg=config();gate=dict(gate_id='abs_2p4',family='absolute',threshold=2.4);bars=roster(20,start='2024-01-10T14:00Z')
        bars['atr14']=np.resize([1.,2.,3.,4.],len(bars));bars.loc[0,'usable']=False;bars.loc[1,'atr14']=0.
        out=synthetic_paths('ES',5,'fast',gate,'final');payload=dict(product='ES',interval_minutes=5,touch_mode='fast',gate=gate,technical=bars)
        rows=strings(stability(out,payload,'final',cfg));c.reconcile_stability(out,bars,rows,cfg,'final')
        self.assertEqual({r['period'] for r in rows if r['period_kind']=='volatility_bin'},{'Q1','Q2','Q3','Q4','undefined'})
        damaged=[r for r in rows if not(r['period_kind']=='volatility_bin' and r['period']=='Q4')]
        with self.assertRaisesRegex(ValueError,'incomplete scientific inventory'):c.reconcile_stability(out,bars,damaged,cfg,'final')
        damaged=copy.deepcopy(rows);damaged[0].pop('favorable_share')
        with self.assertRaisesRegex(ValueError,'required scientific stability'):c.reconcile_stability(out,bars,damaged,cfg,'final')

    def test_mutually_exclusive_embargo_and_endpoint_audit(self):
        from src.stage3_statistics import _phase_stream
        from tests.test_stage3_reference import Authorization
        cfg=config();bars=roster(130,start='2024-01-02T14:00Z');cfg['periods']['final']=dict(start='2024-01-01',end=bars.available_at.iloc[119].isoformat())
        gate=dict(gate_id='abs_0',family='absolute',threshold=0.)
        _,events=ref.reference_stream(bars,[gate],('slow',))
        payload=dict(product='ES',interval_minutes=5,touch_mode='slow',gate=gate,bars=bars,events=events)
        authorization=Authorization();authorization.start=cfg['periods']['final']['start'];authorization.end=cfg['periods']['final']['end']
        with tempfile.TemporaryDirectory() as d:out,audit,_=_phase_stream(Path(d),cfg,payload,'final',authorization)
        rows=strings(audit);c.reconcile_mask_audit(bars,out,rows,cfg,'final')
        damaged=copy.deepcopy(rows);row=next(r for r in damaged if r['horizon']=='100');row['excluded_endpoint_purge']=str(int(row['excluded_endpoint_purge'])+1)
        with self.assertRaisesRegex(ValueError,'integer/discrete'):c.reconcile_mask_audit(bars,out,damaged,cfg,'final')

    def test_portable_receipts_after_seal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);stage=root/'work';stage.mkdir();local=stage/'table.csv';local.write_text('x\n1\n');external=root/'input.csv';external.write_text('y\n2\n')
            result=c.portable_pins(stage,[c.record(local),c.record(external)])
            self.assertEqual(result['records'][0]['path'],'table.csv');self.assertEqual(result['external_records'][0]['path'],str(external.resolve()))
            sealed=root/'run';stage.rename(sealed)
            for pin in result['consumed']:self.assertEqual(c.sha256(c.resolve_pin(sealed,pin)),pin['sha256'])

    def test_empty_acceptance_and_session_week_boundary(self):
        bars=roster(4);gate=dict(gate_id='abs_999',family='absolute',threshold=999.)
        _,events=ref.reference_stream(bars,[gate],('fast',));self.assertTrue(events.empty)
        out=ref.reference_outcomes(bars,events,config(),'development');self.assertTrue(out.empty);self.assertIn('terminal_signal_idx',out)
        f=pd.DataFrame(dict(status=['completed'],terminal_delta_atr=[1.],session=['2024-01-08'],week=['2024-01-01']))
        with self.assertRaisesRegex(ValueError,'outside period roster'):ref.weekly_sufficient(f,'terminal_delta_atr',['2024-01-01'],'session')


class RecoveryDependencyTests(unittest.TestCase):
    """Recovery is a byte dependency, never a substituted numerical reference."""
    names = ('adopted-recovery-packets.json', 'development-recovery-freeze.json',
             'development-recovery-completion.json')
    cfg = dict(development_recovery=dict(expected_adopted_gateways=187,
        expected_missing_gateways=[['NQ',3,'slow',g] for g in ('atr_0p4','atr_0p5','atr_0p75','atr_1','atr_1p5')]))

    def fixture(self, root):
        stage = root / 'work'; (stage / 'provenance').mkdir(parents=True)
        local = stage / 'driver.py'; local.write_text('retained synthetic driver bytes\n')
        external = root / 'original-ledger'; external.write_text('retained synthetic ledger bytes\n')
        lp = c.record(local) | dict(path='driver.py')
        ep = c.record(external)
        for name in self.names:
            (stage / 'provenance' / name).write_text(json.dumps(dict(status='passed', phase='development',
                gateway_count=192, adopted_count=187, missing_count=5,
                records=[lp], external_records=[ep])) + '\n')
        return stage, local, external

    def test_optional_flag_and_all_required_receipts_before_any_science(self):
        from src import stage3_parallel_reconcile as parallel
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertEqual(c.recovery_dependency_pins(root, {}), [])
            stage, _, _ = self.fixture(root)
            (stage / 'config.json').write_text(json.dumps(self.cfg))
            for name in self.names:
                path = stage / 'provenance' / name; original = path.read_bytes(); path.unlink()
                try:
                    for verify in (lambda: c.verify_bundle(stage, 'development'),
                                   lambda: parallel.verify_bundle(stage, workers=1),
                                   lambda: c.verify_bundle(stage, 'complete')):
                        with self.assertRaisesRegex(ValueError, 'required recovery dependency receipt absent'):
                            verify()
                finally:
                    path.write_bytes(original)

    def test_generic_local_external_pins_and_portability(self):
        from src import stage3_parallel_reconcile as parallel
        with tempfile.TemporaryDirectory() as d:
            stage, local, external = self.fixture(Path(d))
            pins = c.recovery_dependency_pins(stage, self.cfg)
            self.assertEqual(len(pins), 5)
            parallel.assert_pins(pins)
            receipt = c.portable_pins(stage, pins)
            self.assertEqual(len(receipt['records']), 4)
            self.assertEqual(receipt['external_records'][0]['path'], str(external.resolve()))
            sealed = stage.with_name('sealed'); stage.rename(sealed)
            for pin in receipt['consumed']:
                self.assertEqual(c.sha256(c.resolve_pin(sealed, pin)), pin['sha256'])
            external.write_text('changed after verification\n')
            with self.assertRaisesRegex(ValueError, 'source/input drift'):
                parallel.assert_pins([p | dict(path=str(c.resolve_pin(sealed, p))) for p in receipt['consumed']])

    def test_status_inventory_and_source_byte_mutations_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            stage, local, external = self.fixture(Path(d))
            cfg = self.cfg
            path = stage / 'provenance' / self.names[1]; original = path.read_bytes()
            for change in ({'status':'failed'}, {'phase':'validation'}, {'records':None},
                           {'records':[c.record(external)]},
                           {'records':[c.record(external) | dict(path='../original-ledger')]},
                           {'external_records':[c.record(local) | dict(path='driver.py')]},
                           {'records':[c.record(local) | dict(path='driver.py', bytes=True)]}):
                path.write_text(json.dumps(json.loads(original) | change))
                with self.assertRaises(ValueError):c.recovery_dependency_pins(stage, cfg)
            path.write_bytes(original)
            before = local.read_bytes(); local.write_text('corrupted driver\n')
            with self.assertRaisesRegex(ValueError, 'recovery dependency bytes changed'):
                c.recovery_dependency_pins(stage, cfg)
            local.write_bytes(before)
            value = json.loads(original)
            value['records'][0]['sha256'] = '0' * 64
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'conflicting recovery dependency pin'):
                c.recovery_dependency_pins(stage, cfg)
            path.write_bytes(original)
            completion = stage / 'provenance' / self.names[2]; original_completion = completion.read_bytes()
            for change in ({'gateway_count':191}, {'adopted_count':187.00000000001}, {'missing_count':True}):
                completion.write_text(json.dumps(json.loads(original_completion) | change))
                with self.assertRaisesRegex(ValueError, 'exact recovery completion'):
                    c.recovery_dependency_pins(stage, cfg)

    def test_complete_rechecks_and_retains_recovery_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            stage, local, external = self.fixture(Path(d))
            cfg = self.cfg
            (stage / 'config.json').write_text(json.dumps(cfg))
            observed = c.portable_pins(stage, c.recovery_dependency_pins(stage, cfg))
            for phase in ('development', 'validation', 'final', 'recent'):
                receipt = dict(status='passed', phase=phase, checks=[dict(check='synthetic_dependency_fixture', status='passed')],
                    consumed=observed['consumed'] if phase == 'development' else [], pins=[])
                (stage / 'provenance' / f'independent-{phase}.json').write_text(json.dumps(receipt))
                if phase != 'development':
                    (stage / 'tables').mkdir(exist_ok=True)
                    (stage / 'tables' / f'S3-T14_{phase}_effects.csv').write_text('synthetic\n')
            with patch.object(c, 'contrast_inventory'), patch.object(c, 'reconcile_final_assessment', return_value=None):
                result = c.verify_bundle(stage, 'complete')
            expected = {p['path'] for p in observed['consumed']}
            self.assertTrue(expected <= {p['path'] for p in result['consumed']})
            (stage / 'provenance' / self.names[2]).write_text('{}\n')
            with self.assertRaisesRegex(ValueError, 'passing recovery dependency required'):
                c.verify_bundle(stage, 'complete')

if __name__=='__main__':unittest.main()

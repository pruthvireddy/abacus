"""The corrected presentation must use 3-minute saved evidence, including support."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pandas as pd

STUDY=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(STUDY))
from src.reporting import render

spec=importlib.util.spec_from_file_location('study28_seal_for_tests',STUDY/'seal.py')
sealer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sealer)


class CorrectedPresentationTests(unittest.TestCase):
    def prepare(self,stage):
        (stage/'tables').mkdir()
        (stage/'figures').mkdir()
        (stage/'config.json').write_text(json.dumps({
            'protocol_version':'1.1.0','primary_timeframe':'3m','timeframes':['3m'],
            'common_calendar':['2021-06-28','2026-09-18'],
            'bootstrap':{'replicates':2000,'block_observed_sessions':5}}))
        rows=[]
        for i,product in enumerate(['ES','NQ','GC']):
            for cohort in ['common_calendar','matched_dates']:
                for segmentation,regime,mean in [('all','all',4.25+i),
                        ('atr_regime','low',5.25+i),('atr_regime','high',3.25+i),
                        ('realized_regime','quiet',2.25+i),('realized_regime','active',6.25+i)]:
                    rows.append({'product':product,'timeframe':'3m','window':'globex',
                        'cohort':cohort,'segmentation':segmentation,'regime':regime,
                        'sessions':17 if cohort=='matched_dates' else 52+i,
                        'mean_crosses':mean,'median_crosses':2+i,'p25_crosses':1.,
                        'p75_crosses':7.,'p90_crosses':8.,'mean_ci95_low':mean-.5,
                        'mean_ci95_high':mean+.5,'small_cell':False})
            overall=next(r for r in rows if r['product']==product and r['cohort']=='common_calendar' and r['segmentation']=='all')
            rows.append({**overall,'window':'us_cash'})
            if product=='GC':rows.append({**overall,'window':'gc_day'})
        pd.DataFrame(rows).to_csv(stage/'tables/summary.csv',index=False)
        annual=[{**r,'year':2025} for r in rows if r['segmentation']=='all']
        pd.DataFrame(annual).to_csv(stage/'tables/yearly.csv',index=False)

    def test_report_and_findings_use_corrected_timeframe_and_saved_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            self.prepare(stage)
            render(stage)
            sealer.findings(stage)
            report=(stage/'report.md').read_text()
            self.assertIn('6-period EMA of closing prices on 3-minute bars',report)
            self.assertIn('ES 4.25 (n=52)',report)
            self.assertIn('Corresponding medians were ES 2, NQ 3, GC 4.',report)
            self.assertIn('17 shared eligible dates',report)
            self.assertIn('ES 2.25/6.25',report)
            self.assertNotIn('quiet-greater-than-active',report)
            self.assertNotIn('5-minute',report)
            self.assertNotIn('2-minute',report)
            self.assertIn('No published 3-minute VWAP release is claimed or created',report)
            self.assertIn('first included bar opens at 08:21',report)
            self.assertIn('known after the session',report)
            metrics=json.loads((stage/'metrics.json').read_text())
            self.assertEqual(metrics['primary_timeframe'],'3m')
            self.assertEqual([r['median_crosses'] for r in metrics['rows']],[2,3,4])
            page=(stage/'report.html').read_text()
            self.assertIn('Corresponding medians were ES 2, NQ 3, GC 4.',page)

    def test_corrected_renderer_refuses_other_timeframes(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            self.prepare(stage)
            config=json.loads((stage/'config.json').read_text())
            config.update(primary_timeframe='5m',timeframes=['5m','2m'])
            (stage/'config.json').write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError,'3-minute-only'):
                render(stage)
            self.assertFalse((stage/'report.md').exists())

    def test_supplementary_checks_disclose_current_scope(self):
        with tempfile.TemporaryDirectory() as temp:
            stage=Path(temp)
            (stage/'checks').mkdir()
            (stage/'checks/owned-suite-harness.json').write_text(json.dumps({'exit_code':0}))
            (stage/'checks/optional.json').write_text(json.dumps({'exit_code':None}))
            checks={r['name']:r for r in sealer.supplementary_checks(stage)}
            self.assertEqual(checks['owned-suite-harness']['status'],'passed')
            self.assertEqual(checks['optional']['status'],'not_run')
            self.assertEqual(checks['workspace-default']['status'],'not_run')
            (stage/'checks/workspace-default.json').write_text(json.dumps({'exit_code':1}))
            checks={r['name']:r for r in sealer.supplementary_checks(stage)}
            self.assertEqual(checks['workspace-default']['status'],'failed')


if __name__=='__main__':unittest.main()

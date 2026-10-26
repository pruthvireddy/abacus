"""Independent checker fixtures use synthetic prices, including deliberate corruption."""
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.stage2_engine import generate_streams
from src.stage2_membership import build_membership
from src.outcomes import score_outcomes
from src.stage2_statistics import (summarize_branches, quantiles_branches, stability_branches,
    support_roster, coverage_columns, union_outcomes, signal_flow_branches, geometry_membership,
    episode_pair_metrics, episode_summary, union_summary)
from src.stage2_reconcile import (reconcile_stream, reconcile_paths, reconcile_memberships,
    reconcile_dual_union, reconcile_summary_tables, reconcile_calendar_support,
    reconcile_new_diagnostics, reconcile_flow)
from src.stage2_reference import in_development


def synthetic_cell(product='ES', interval=5, start='2018-01-02T14:00Z'):
    n = 130
    times = pd.date_range(start, periods=n, freq=f'{interval}min')
    frame = pd.DataFrame(dict(timestamp=times, available_at=times + pd.Timedelta(minutes=interval),
        product=product, interval_minutes=interval, contract=product+'H8', open=125., high=126., low=124.,
        close=125., volume=10., ema20=120., ema50=100., atr14=2., usable=True,
        feature_valid=True, feature_reset=False, consecutive_count=250, session='2018-01-02',
        quality_reason='complete', known_closure_before=False, feature_source_timestamp=times,
        feature_available_at=times + pd.Timedelta(minutes=interval), feature_contract=product+'H8'))
    frame.loc[1, ['low','high','close']] = [119., 125., 122.]
    frame.loc[2:3, ['low','high','close']] = [99., 125., 112.]
    frame.loc[20:21, ['low','high','close']] = [99., 125., 112.]
    frame.loc[128:, ['low','high','close']] = [119., 125., 122.]
    technical, causal = generate_streams(frame, interval)
    technical = technical.sort_values(['timestamp','touch_mode'], kind='stable').reset_index(drop=True)
    members = build_membership(frame, technical, causal)
    events = causal[causal.timestamp.map(in_development)].copy()
    hs = (5,10,15,20,30,50,100) if interval == 3 else (5,10,12,15,20,30,50,100)
    outcomes = score_outcomes(frame, events, hs, interval, roster_end_is_endpoint=True)
    selected = members['union']
    projected = union_outcomes(selected, outcomes)
    projected['source_event_id'] = projected.representative_event_id
    return frame, technical, events, outcomes, members, projected


class Stage2ReconcileTests(unittest.TestCase):
    def test_scalar_acceptance_matches_both_producers_and_catches_corrupted_arm(self):
        bars, tech, events, _, _, _ = synthetic_cell()
        receipt, causal = reconcile_stream(bars, tech, events)
        self.assertEqual(receipt['technical_rows'], 260)
        self.assertEqual(len(causal), len(events))
        bad = tech.copy()
        bad.loc[bad.touch_mode.eq('fast') & bad.signal_idx.eq(1), 'armed_before'] = False
        with self.assertRaises(ValueError):
            reconcile_stream(bars, bad, events)

    def test_all_paths_and_carried_identity_are_checked(self):
        bars, _, events, outcomes, _, _ = synthetic_cell(interval=3)
        self.assertEqual(reconcile_paths(bars, events, outcomes)['rows'], len(outcomes))
        for field, value in (('contract','CORRUPTED'), ('ema20',-999.), ('signal_idx',999), ('entry_atr',9.)):
            bad = outcomes.copy()
            bad.loc[0,field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                reconcile_paths(bars, events, bad)

    def test_membership_contact_null_and_union_representative_provenance(self):
        bars, tech, events, outcomes, members, projected = synthetic_cell()
        receipt, causal = reconcile_stream(bars, tech, events)
        self.assertEqual(reconcile_memberships(bars, tech, causal, members)['status'], 'passed')
        self.assertEqual(reconcile_dual_union(events,outcomes,members['union'],projected)['status'],'passed')
        bad = {k:v.copy() for k,v in members.items()}
        bad['pairs'].loc[bad['pairs'].pair_relation.eq('fast_only'),'strictly_later_slow_contact'] = False
        with self.assertRaises(ValueError):
            reconcile_memberships(bars, tech, causal, bad)
        corrupt = projected.copy()
        corrupt.loc[0,'source_event_id'] = 'wrong-source'
        with self.assertRaises(ValueError):
            reconcile_dual_union(events,outcomes,members['union'],corrupt)

    def test_complete_summaries_quantiles_calendar_and_dropped_duplicate_mutations(self):
        _, tech, _, outcomes, _, _ = synthetic_cell()
        roster,sessions = support_roster(tech)
        summary = summarize_branches(outcomes,('all','same_session','uninterrupted'))
        stability = coverage_columns(stability_branches(outcomes,sessions),roster)
        quantile = quantiles_branches(outcomes)
        frames = {'S2-T02':summary,'S2-T03':quantile,
            'S2-T04':stability[~stability.period_kind.isin(['week','month'])],
            'S2-T05':stability[stability.period_kind.isin(['week','month'])]}
        with tempfile.TemporaryDirectory() as directory:
            paths = {k:Path(directory)/(k+'.csv') for k in frames}
            for k,f in frames.items(): f.to_csv(paths[k],index=False,float_format='%.17g')
            self.assertEqual(reconcile_summary_tables(outcomes,paths,session_roster=sessions)['status'],'passed')
            self.assertEqual(reconcile_calendar_support(tech,paths)[0]['status'],'passed')
            bad=frames['S2-T05'].copy()
            bad.loc[bad.index[0],'eligible_slots'] += 1
            bad.to_csv(paths['S2-T05'],index=False,float_format='%.17g')
            with self.assertRaises(ValueError): reconcile_calendar_support(tech,paths)
            frames['S2-T05'].to_csv(paths['S2-T05'],index=False,float_format='%.17g')
            for mutation in ('drop','duplicate'):
                bad=summary.iloc[1:].copy() if mutation=='drop' else pd.concat([summary,summary.iloc[:1]],ignore_index=True)
                if mutation=='duplicate': bad.loc[len(bad)-1,'row_id']='distinct-duplicate'
                bad.to_csv(paths['S2-T02'],index=False,float_format='%.17g')
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                    reconcile_summary_tables(outcomes,paths,session_roster=sessions)

    def test_all_geometry_pair_union_flow_cells_and_first_pair_differences(self):
        _,tech,events,outcomes,members,projected=synthetic_cell()
        metrics=episode_pair_metrics(members['pairs'],outcomes)
        frames={'S2-T07':geometry_membership(members['membership']),
            'S2-T09':episode_summary(members['pairs'],metrics),
            'S2-T10':union_summary(members['membership'],members['union'],outcomes,projected),
            'S2-T01':signal_flow_branches(tech,events,outcomes)}
        with tempfile.TemporaryDirectory() as directory:
            paths={k:Path(directory)/(k+'.csv') for k in frames}
            for k,f in frames.items():f.to_csv(paths[k],index=False,float_format='%.17g')
            metric_path=Path(directory)/'pairs.csv'
            metrics.to_csv(metric_path,index=False,float_format='%.17g')
            self.assertEqual(reconcile_new_diagnostics(members['membership'],members['pairs'],members['union'],outcomes,paths,metric_path)['status'],'passed')
            self.assertEqual(reconcile_flow(tech,outcomes,paths['S2-T01'])['status'],'passed')
            frames['S2-T07'].iloc[1:].to_csv(paths['S2-T07'],index=False,float_format='%.17g')
            with self.assertRaisesRegex(ValueError,'geometry inventory'):
                reconcile_new_diagnostics(members['membership'],members['pairs'],members['union'],outcomes,paths,metric_path)


if __name__ == '__main__': unittest.main()

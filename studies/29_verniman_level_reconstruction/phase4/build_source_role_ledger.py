#!/usr/bin/env python3
"""Project only the gate-approved, byte-pinned ten-date source selection.

No release loader/network/source discovery or market model is invoked. Original
Phase2 occurrences stay intact. Canonical plan roles, user recollections and
closing/execution observations remain explicitly separate evidence classes.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
STAGE = ROOT / 'work/29_verniman_level_reconstruction/phase4_20261031T010249Z'
DATES = ('2026-10-01','2026-10-02','2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12','2026-10-13','2026-10-14')
FAMILIES = {'YVAH','YPOC','YVAL','YVALH','YHOD','YLOD','ONH','ONL','HVE','HVN','LVN','PBT','GAP','VPOC','ATH','RTH','ON','IVL','VAR','CPI','SOC'}
SUPPORTED = {'YVAH','YPOC','YVAL','ONVAH','ONPOC','ONVAL','ONH','ONL','YHOD','YLOD','PRIOR_CLOSE','CWVAH','CWPOC','CWVAL','PWVAH','PWPOC','PWVAL','HVN','LVN','HVE','PBT'}


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p): return {'path':str(p.relative_to(ROOT)), 'sha256':digest(p)}
def read(p): return json.loads(p.read_text())
def write_new(p,x):
    with p.open('x') as f: json.dump(x,f,indent=2);f.write('\n')
def families(label):
    tokens = re.findall(r'[A-Z]+', (label or '').upper().replace('PBTS','PBT').replace('GAPS','GAP'))
    return list(dict.fromkeys(t for t in tokens if t in FAMILIES)) or ['UNRESOLVED_LABEL']
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main():
    gate = module('phase4_source_gate', PHASE/'select_sources.py')
    receipt=gate.validate_gate(ROOT, STAGE, STAGE/'reveal-gate-revision2.json')
    review=read(STAGE/'root-reveal-review.json')
    selection=read(STAGE/'source-selection-manifest-release13.json')
    if selection['authorized_dates'] != list(DATES) or selection['dataset']['version'] != '13.0.0':
        raise ValueError('exact approved release/date selection required')
    # Verify selected bytes before any source text is loaded.
    for table,dates in selection['tables'].items():
        for day,p in dates.items():
            if day not in DATES or digest(STAGE/p['path'])!=p['sha256']: raise ValueError('selected table pin differs')
    for p in selection['intake']:
        if p['session_date'] not in DATES or digest(STAGE/p['selected_path'])!=p['selected_sha256']: raise ValueError('selected intake pin differs')
    backup=STAGE/'source-role-ledger-pre-reveal.json'
    if not backup.exists(): backup.write_bytes((PHASE/'source-role-ledger.json').read_bytes())
    old=read(backup)
    if old['source_occurrence_count']!=143 or {r['session_date'] for r in old['occurrences']}!=set(DATES[:3]):
        raise ValueError('original143 source projection required')
    result=deepcopy(old); rows=result['occurrences']; sessions=[]
    used=[]
    def load(relative):
        path=STAGE/relative; used.append(pin(path));return read(path)
    def occurrence(day, sid, oid, label, low, high, sourceclass, raw, parent, role='structural_reference_without_selected_scenario_role', side=None, order=None):
        fs=families(label)
        return {'level_id':oid,'session_date':day,'source_id':sid,'original_label':label,'exact_readable_source_text':label,
            'price_low':low,'price_high':high,'price_basis':'printed' if low is not None else 'unpriced_label',
            'reading_uncertainty':'Literal retained transcription; rounding convention and exact source calculation unknown.' if low is not None else 'No exact numeric source coordinate; nearby axis values are not substituted.',
            'families':fs,'reference_period':'unresolved_exact_source_window','developing_or_completed':'unresolved',
            'instrument':parent.get('product') or parent.get('instrument_raw'),'actual_contract':parent.get('contract'),
            'contract_identity_basis':'Printed canonical plan contract.' if sourceclass=='named_daily_plan' else 'Original evidence metadata; missing identity remains null.',
            'source_timing_class':'unresolved','available_at':raw.get('available_at'),
            'preopen_status':'historical_availability_unverified; capture, claimed update and recollected read time are not certified availability',
            'provenance':{'source_revision_id':parent.get('source_revision_id') or parent.get('observation_id'),
                'source_posted_at':parent.get('posted_at') or parent.get('source_claimed_published_at'),
                'source_claimed_updated_at':parent.get('source_claimed_updated_at'),
                'capture_timestamp':parent.get('captured_at') or parent.get('recorded_at'),
                'source_url':parent.get('source_url') or parent.get('post_url')},
            'source_class':sourceclass,'source_kind':sourceclass,'apparent_role':raw.get('role') or 'structural reference',
            'scenario_side':side,'source_target_order':order,'phase4_role':role,
            'role_basis':'Explicit canonical conditional branch and original ordinal.' if sourceclass=='named_daily_plan' and role!='structural_reference_without_selected_scenario_role' else 'Retained evidence role only; not promoted to canonical scenario ground truth.',
            'literal_source_LIS_label':bool(re.search(r'\bLIS\b',label or '')),
            'directional_conditions':raw.get('conditions'),'vix_cvd_input_status':'unmeasured_not_substituted',
            'origin':{'kind':sourceclass,'original_role':raw.get('role'),'original_label':raw.get('source_label'),'source_record':raw},
            'source_identity':parent,
            'candidate_explanations':['Printed family suggests a named auction boundary, extreme or projection; its exact window/anchor construction is unverified.'],
            'competing_explanations':['Different feed/session/profile/anchor, source rounding, retained revision conflict or unsupported reference family.'],
            'comparison':{'status':'pending_saved_pre_reveal_map_analysis','strict_candidate_availability':None,'construction_window_identity_supported':None,'selector_chose_source_reference':None,'scenario_role_and_order_agreement':None,'strict_family_window_coverage':None,'unsupported_or_unresolved_roles':[f for f in fs if f not in SUPPORTED],'post_cutoff_reaction_used':False}}
    roleunits=module('phase4_source_units',PHASE/'source_roles.py')
    for day in DATES:
        if day in DATES[:3]:
            session=deepcopy(next(x for x in old['session_records'] if x['session_date']==day))
            session.update(source_review_status='previously_exposed_Phase2_inventory_preserved',expanded_candidate_map_status='saved_pre_reveal_local_attempt3',selector_evaluation_status='pending_saved_map_analysis')
            sessions.append(session);continue
        canon=load(f'selected-sources-release13/release/{day}/outlooks.json')
        levelrows=load(f'selected-sources-release13/release/{day}/levels.json')
        sourceissues=load(f'selected-sources-release13/release/{day}/issues.json')
        coverage=load(f'selected-sources-release13/release/{day}/coverage.json')
        byid={x['outlook_id']:x for x in canon}; dayrows=[]
        for raw in levelrows:
            p=byid[raw['outlook_id']]; sid='B-'+day.replace('-','')+'-'+raw['outlook_id'][:12]
            oid=sid+'-PLAN-'+raw['side']+'-'+raw['role']+'-'+str(raw['ordinal'])
            role='conditional_scenario_divider' if raw['role']=='trigger' else 'ordered_'+raw['side']+'_destination' if raw['role']=='target' else 'structural_reference_without_selected_scenario_role'
            dayrows.append(occurrence(day,sid,oid,raw['source_text'],raw['price_low'],raw['price_high'],'named_daily_plan',raw,p,role,raw['side'],raw['ordinal'] if raw['role']=='target' else None))
        for p in canon:
            # Header values are structural references, never selected targets.
            header=re.search(r'ESZ26[^\n]*',p.get('body_text') or '')
            for label,price in re.findall(r'\b(YVAH|YPOC|YVAL|GAP)\s+([0-9]+(?:\.[0-9]+)?)',header.group() if header else ''):
                sid='B-'+day.replace('-','')+'-'+p['outlook_id'][:12]
                dayrows.append(occurrence(day,sid,sid+'-HEADER-'+label,label+' '+price,price,price,'named_daily_plan',{'role':'header_reference','source_label':label},p))
        recollections=load(f'selected-sources-release13/user-recollections/{day}/observations.json')
        recalled=load(f'selected-sources-release13/user-recollections/{day}/observation_levels.json')
        recalledbyid={x['observation_id']:x for x in recollections}
        for raw in recalled:
            p=recalledbyid[raw['observation_id']]; sid='RECOLLECTION-'+p['observation_id'][:12]
            role='reported_divider_recollection' if raw['role']=='trigger' else 'recalled_ordered_'+raw['side']+'_destination' if raw['role']=='target' else 'structural_reference_without_selected_scenario_role'
            oid=sid+'-'+raw['side']+'-'+raw['role']+'-'+str(raw['ordinal'])
            dayrows.append(occurrence(day,sid,oid,raw['source_text'],raw['price_low'],raw['price_high'],'user_supplied_recollection',raw,p,role,raw['side'],raw['ordinal'] if raw['role']=='target' else None))
        annotations=[]; executions=[]; intakeissues=[]; intakepins=[]
        for selected in [x for x in selection['intake'] if x['session_date']==day]:
            observation=load(selected['selected_path']); intakepins.append({'path':str((STAGE/selected['selected_path']).relative_to(ROOT)),'sha256':selected['selected_sha256']})
            sourcebyid={x['source_id']:x for x in observation['sources']}
            for raw in observation['closing_notes']:
                parent={**sourcebyid[raw['source_id']], 'observation_id':observation['observation_id'], 'source_revision_id':observation['observation_id']}
                if raw['category']=='reference_level':
                    sid='X-'+raw['source_id'];oid=sid+'-'+observation['observation_id']+'-'+raw['note_id']
                    dayrows.append(occurrence(day,sid,oid,raw['label_raw'],raw.get('numeric_value'),raw.get('numeric_value'),'closing_chart_reference',raw,parent))
                else: annotations.append({'observation_id':observation['observation_id'],**raw})
            executions.extend({'observation_id':observation['observation_id'],**m} for m in observation['markers'])
            intakeissues.extend(observation.get('issues',[]))
        rows.extend(dayrows)
        canonical=[r for r in dayrows if r['source_class']=='named_daily_plan' and r['phase4_role']!='structural_reference_without_selected_scenario_role']
        status='reviewed' if canonical else 'source_suitability_failure'
        sessions.append({'session_date':day,'source_review_status':status,'failure_reasons':[] if canonical else ['NO_DATED_CANONICAL_PLAN_IN_RELEASE13; closing chart/execution references do not establish preopen pivot or ordered scenario destinations.'],
            'source_occurrence_ids':[r['level_id'] for r in dayrows], 'source_role_counts':dict(Counter(r['phase4_role'] for r in dayrows)),
            'selected_source_refs':[r['level_id'] for r in canonical], 'canonical_source_revision_ids':list(byid),
            'functional_divider_interpretations':roleunits.interpret_divider_strata(canonical),
            'ordered_source_destinations':{side:[{'source_occurrence_id':r['level_id'],'source_revision_id':r['provenance']['source_revision_id'],'order':r['source_target_order'],'original_label':r['original_label'],'price_interval':[r['price_low'],r['price_high']]} for r in canonical if r['phase4_role']=='ordered_'+side+'_destination'] for side in ('bullish','bearish')},
            'source_sequence_qualification':'Full source order preserved per class/revision. Three executable targets never truncate source denominators. Recollections and closing charts remain separate evidence classes.',
            'explicit_invalidation_references':{'status':'not_identified_as_separate_canonical_role','occurrence_ids':[],'qualification':'Conditional branch crossing is not automatically an explicit stop/invalidation.'},
            'execution_annotations':{'status':'retained_separately_never_pivot_target_truth','records':executions},
            'other_source_annotations':annotations,'source_issues':sourceissues,'intake_issues':intakeissues,'coverage_records':coverage,
            'intake_pins':intakepins,'available_at':None,'source_historical_availability':'unresolved', 'expanded_candidate_map_status':'saved_pre_reveal_local_attempt3','selector_evaluation_status':'pending_saved_map_analysis',
            'exact_window_coverage':None,'exposure_status':'training_answers_reviewed_after_gate','out_of_sample':False})
    if len({r['level_id'] for r in rows})!=len(rows):
        raise ValueError('duplicate source occurrence ID: '+str([k for k,v in Counter(r['level_id'] for r in rows).items() if v>1]))
    if rows[:143]!=old['occurrences']: raise ValueError('original143 occurrences changed')
    result.update(scope='All ten authorized training sessions; original143 Phase2 occurrences retained unchanged, seven exact-date selected source projections reviewed after passed gate. No development/hidden sources read.',source_occurrence_count=len(rows),session_records=sessions,
        recorded_at=datetime.now(timezone.utc).isoformat(),new_answer_sources_opened_by_this_projection=True,
        previous_ledger=pin(backup),source_selection=pin(STAGE/'source-selection-manifest-release13.json'),reveal_gate=receipt['gate'],root_reveal_review=pin(STAGE/'root-reveal-review.json'),
        projection_code=pin(Path(__file__)),additional_source_pins=list({p['path']:p for p in used}.values()),
        role_policy='Canonical branch triggers/destinations define scenario ground truth per independent class/revision. User recollections retain explicitly recalled roles; closing-chart labels remain structural. No favorable revision selection, nearest trigger, averaging, source-price candidate insertion or timing repair.',
        team_exposure_caveat='Parent reported an inadvertent separate-agent read of a mutable general data guide containing protected hidden-answer snippets after these ten maps and policies were frozen. This projection reads only the bounded selected ten-date sources; it does not claim pristine team-wide hidden exposure. Parent retains the incident audit; later hidden evaluation requires a fresh unexposed evaluator.',
        selection_parameters_refitted_after_reveal=False)
    (PHASE/'source-role-ledger.json').write_text(json.dumps(result,indent=2)+'\n')
    write_new(STAGE/'source-role-ledger-post-reveal-manifest.json',{'schema':'abacus.study29.phase4.source-projection/v1','ledger':pin(PHASE/'source-role-ledger.json'),'previous_ledger':pin(backup),'projection':pin(Path(__file__)),'source_selection':result['source_selection'],'source_occurrence_count':len(rows),'canonical_plan_rows':sum(r['source_class']=='named_daily_plan' and r['phase4_role']!='structural_reference_without_selected_scenario_role' for r in rows),'session_status':{s['session_date']:s['source_review_status'] for s in sessions},'original143_unchanged':True,'gate':receipt['gate']})
    print(json.dumps({'occurrences':len(rows),'canonical_plan_rows':sum(r['source_class']=='named_daily_plan' and r['phase4_role']!='structural_reference_without_selected_scenario_role' for r in rows),'ledger_sha256':digest(PHASE/'source-role-ledger.json'),'session_status':{s['session_date']:s['source_review_status'] for s in sessions}},indent=2))

if __name__=='__main__':main()

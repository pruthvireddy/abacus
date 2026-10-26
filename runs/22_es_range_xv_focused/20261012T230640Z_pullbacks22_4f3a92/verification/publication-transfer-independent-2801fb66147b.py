"""Independent saved-table transfer audit; standard library, no producer imports."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

GROUP = ('year', 'timeframe_id', 'direction', 'earlier_leg_bucket')
COHORTS = ('all', *map(str, range(1, 11)), '11-15', '16-20', '21+', 'unknown_start')
WINDOWS = ('all_hours', 'asia', 'london', 'ny', 'asia_open', 'ny_open', 'ny_am', 'ny_pm')
LABELS = dict(zip(WINDOWS, ('All hours', 'Asia', 'London', 'NY', 'Asia Open', 'NY Open', 'NY AM', 'NY PM')))
DIRECTIONS = {'bullish': 'Bullish resumption R', 'bearish': 'Bearish resumption R', 'all': 'Both directions'}
TABLES = {'summary': 9720, 'continuation': 194400, 'retracement': 38880, 'payoff': 19440, 'coverage': 216}
PIVOTS = {'probabilities.csv': 'probability', 'successes.csv': 'numerator', 'known-outcomes.csv': 'denominator', 'unknown-outcomes.csv': 'unknown_count'}
CSV_PROJECTIONS = {
    'retracement-recovery.csv': ('retracement', [*GROUP, 'level_percent', 'event_count', 'valid_f1_count',
        'unknown_f1_count', 'touch_count', 'touch_probability', 'joint_beyond_close_numerator',
        'joint_beyond_close_denominator', 'joint_beyond_close_probability', 'conditional_beyond_close_numerator',
        'conditional_beyond_close_denominator', 'conditional_beyond_close_probability']),
    'setup-samples.csv': ('summary', [*GROUP, 'event_count', 'exact_followup_count', 'censored_followup_count',
        'known_f1_count', 'unknown_f1_count', 'earlier_start_known_count', 'earlier_start_unknown_count',
        'sessions_with_events', 'sessions_with_known_f1', 'eligible_bar_count', 'covered_sessions',
        'first_session_date', 'last_session_date', 'bar_coverage_anchor', 'event_membership_anchor']),
    'gross-ohlc-payoff.csv': ('payoff', [*GROUP, 'target_multiple', 'horizon_candles', 'event_count',
        'valid_entry_count', 'invalid_entry_count', 'unknown_entry_count', 'known_outcome_count',
        'unknown_outcome_count', 'resolved_count', 'ambiguous_count', 'marked_count', 'win_lower_numerator',
        'win_upper_numerator', 'denominator', 'win_rate_lower', 'win_rate_upper', 'mean_lower_r', 'mean_upper_r',
        'sessions_with_events', 'sessions_with_known_outcome']),
    'payoff-resolution.csv': ('payoff', [*GROUP, 'target_multiple', 'horizon_candles', 'event_count',
        'valid_entry_count', 'invalid_entry_count', 'unknown_entry_count', 'known_outcome_count',
        'unknown_outcome_count', 'resolved_count', 'ambiguous_count', 'marked_count', 'target_touch_count',
        'stop_touch_count', 'gap_target_count', 'gap_stop_count', 'payoff_lower_sum_r', 'payoff_upper_sum_r',
        'sessions_with_events', 'sessions_with_valid_entry', 'sessions_with_known_outcome']),
}

def expected_columns(section):
    """Authored numeric fields and formats, independent of producer bindings."""
    if section.startswith('n'):
        parts = section.split('-')
        lo, hi = int(parts[0][1:]), int(parts[1])
        return [(f'n{n}', 'percent') for n in range(lo, hi + 1)]
    if section.startswith('counts-'):
        return [(c, 'number') for c in ('e', 'f', 'u', 'c', 's')]
    if section.startswith('overall-') and section != 'overall-payoff':
        return [(c, 'percent' if c == 'p' else 'number') for c in ('n', 's', 'd', 'u', 'p')]
    if section == 'overall' or section.startswith('depth-'):
        columns = ('l', 'f', 'u', 't', 'p', 'j', 'q', 'r') if section == 'overall' else ('f', 'u', 't', 'p', 'j', 'q', 'r')
        return [(c, 'percent' if c in ('p', 'q', 'r') else 'number') for c in columns]
    if section == 'overall-payoff' or section.startswith('target-'):
        columns = ('t', 'e', 'k', 'u', 'i', 'a', 'lo', 'hi', 'wl', 'wh') if section == 'overall-payoff' else ('e', 'k', 'u', 'i', 'a', 'lo', 'hi', 'wl', 'wh')
        return [(c, 'percent' if c in ('wl', 'wh') else 'number') for c in columns]
    raise ValueError(f'Unexpected numeric section {section}')

def require(ok, why):
    if not ok:
        raise ValueError(why)

def sha(path):
    require(path.is_file() and not any(x.is_symlink() for x in (path, *path.parents)), f'Unsafe file {path}')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()

def csv_read(path):
    sha(path)
    with path.open(newline='') as f:
        r = csv.DictReader(f)
        rows = list(r)
        require(None not in r.fieldnames and len(set(r.fieldnames)) == len(r.fieldnames), 'CSV header')
        require(all(None not in row and None not in row.values() for row in rows), 'CSV row width')
        return r.fieldnames, rows

def jl(path):
    sha(path)
    return json.loads(path.read_text())

def yl(y):
    return 'All years' if not y else y + (' (partial)' if y in ('2019', '2026') else '')

def ll(c):
    return 'All earlier legs' if c == 'all' else 'Unknown earlier start' if c == 'unknown_start' else c + (' candle' if c == '1' else ' candles')

def numeric(s):
    return None if s == '' else round(float(s), 6)

def expected_column(section, col, rownum):
    if section == 'coverage':
        return 'summary', ('event_count', 'covered_sessions', 'eligible_bar_count', 'unknown_f1_count')[rownum]
    if section.startswith('counts-'):
        return 'summary', {'e':'event_count', 'f':'known_f1_count', 'u':'unknown_f1_count', 'c':'censored_followup_count', 's':'sessions_with_events'}[col]
    if section.startswith('overall-') and section != 'overall-payoff':
        return 'continuation', {'n':'n', 's':'numerator', 'd':'denominator', 'u':'unknown_count', 'p':'probability'}[col]
    if section.startswith('n'):
        return 'continuation', 'probability'
    if section == 'overall' or section.startswith('depth-'):
        return 'retracement', {'l':'level_percent', 'f':'valid_f1_count', 'u':'unknown_f1_count', 't':'touch_count', 'p':'touch_probability', 'j':'joint_beyond_close_numerator', 'q':'joint_beyond_close_probability', 'r':'conditional_beyond_close_probability'}[col]
    if section == 'overall-payoff' or section.startswith('target-'):
        return 'payoff', {'t':'target_multiple', 'e':'event_count', 'k':'known_outcome_count', 'u':'unknown_outcome_count', 'i':'invalid_entry_count', 'a':'ambiguous_count', 'lo':'mean_lower_r', 'hi':'mean_upper_r', 'wl':'win_rate_lower', 'wh':'win_rate_upper'}[col]
    raise ValueError(f'Unexpected section {section}')

def audit(stage, root, prior):
    script = Path(__file__).resolve()
    script_sha = sha(script)
    vd = stage / 'verification'
    vd.mkdir(exist_ok=True)
    snap = vd / f'publication-transfer-independent-{script_sha[:12]}.py'
    with snap.open('xb') as f:
        f.write(script.read_bytes())
    hashes = {snap.relative_to(stage).as_posix(): sha(snap)}
    tables = {}
    for key, count in TABLES.items():
        rel = 'tables/coverage.csv' if key == 'coverage' else f'tables/pullback_{key}.csv'
        header, rows = csv_read(stage / rel)
        require(len(rows) == count, f'Wrong table count {rel}')
        tables[rel] = (header, rows)
        hashes[rel] = sha(stage / rel)
    producer = jl(stage / 'publication-verification.json')
    require(producer['result'] == 'passed' and producer['run_id'] == stage.name, 'Producer attribution')
    for name, value in producer['artifact_hashes'].items():
        require(sha(stage / name) == value, f'Changed producer input {name}')
        hashes[name] = value
    counts = {'publications':0, 'numeric_cells':0, 'context_rows':0, 'selected_csv_files':0, 'selected_csv_rows':0, 'original_csv_cells':0, 'prior_publication_files':0}
    contexts = [(yl(y), LABELS[w], ll(c)) for y in ('', *map(str, range(2019,2027))) for w in WINDOWS for c in COHORTS]
    folders = sorted((stage / 'publications').iterdir())
    require({p.name for p in folders} == {f'{s}t-{v}' for s in (4,5,6) for v in ('continuation','retracement','payoff')}, 'Nine folders required')
    for folder in folders:
        setting = int(folder.name[0]); view = folder.name.split('-',1)[1]
        report = jl(folder / 'publication.json'); mapping = jl(folder / 'source-map.json'); receipt = jl(folder / 'verification.json')
        require(report['id'] == f'es-range-xv-pullback-{view}-{setting}t-20261012' and report['source'] == {'producer':'sahadeva','runId':stage.name}, 'Report attribution')
        require(mapping['run_id'] == stage.name and mapping['source_hashes'] == {rel: hashes[rel] for rel in tables}, 'Source-map attribution and hashes')
        require(receipt['result'] == 'passed' and receipt['publication_sha256'] == sha(folder / 'publication.json'), 'Per-report receipt hash')
        sections = {s['id']: s for s in report['sections']}
        require(len(sections) == len(report['sections']), 'Duplicate section IDs')
        expected_filtered = ([f'n{lo}-{hi}-{d}' for d in ('bullish','bearish') for lo,hi in ((1,8),(9,16),(17,20))] + [f'counts-{d}' for d in ('bullish','bearish')] if view == 'continuation' else [f'depth-{n}-{d}' for d in ('bullish','bearish') for n in (25,50,75,100)] if view == 'retracement' else [f'target-{n}r-{d}' for d in DIRECTIONS for n in (1,2)])
        overall_ids = [f'overall-{d}' for d in DIRECTIONS] if view == 'continuation' else ['overall'] if view == 'retracement' else ['overall-payoff']
        require(set(sections) == set(expected_filtered + overall_ids + ['definition', 'coverage', 'methods']), 'Complete report section inventory')
        require(sections['coverage']['kind'] == 'metrics' and len(sections['coverage']['items']) == 4, 'Four overall sample metrics required')
        require([i['label'] for i in sections['coverage']['items']] == ['Observed A → B → R setups', 'Covered sessions', 'Eligible completed candles', 'Unknown F1 outcomes'], 'Coverage metric labels')
        for sid in expected_filtered + overall_ids:
            s = sections[sid]
            require(s['kind'] == 'table', 'Declared metric table required')
            contexts_header = ['year', 'window', 'leg'] if sid in expected_filtered else ['direction']
            require([c['key'] for c in s['columns']] == [*contexts_header, *(c for c, _ in expected_columns(sid))], 'Complete numeric table columns')
            require([(c['key'], c.get('format')) for c in s['columns'][len(contexts_header):]] == expected_columns(sid), 'Numeric table formats')
            expected_count = 1080 if sid in expected_filtered else 20 if view == 'continuation' else 12 if view == 'retracement' else 6
            require(len(s['rows']) == expected_count, 'Complete overall or filtered table rows')
        addresses = set()
        filtered_ids = []
        for s in report['sections']:
            if s['kind'] == 'metrics':
                addresses.update((s['id'],'value',i) for i in range(len(s['items'])))
            if s['kind'] != 'table':
                continue
            for i, row in enumerate(s['rows']):
                for col in s['columns']:
                    if col.get('format') in ('number','percent'):
                        addresses.add((s['id'],col['key'],i))
            if 'rowFilters' in s:
                require([(r['year'],r['window'],r['leg']) for r in s['rows']] == contexts, f'Incomplete contexts {s["id"]}')
                require(s['rowFilters'] == [{'key':'year','label':'Year','defaultValue':'All years'}, {'key':'window','label':'Session / timeframe','defaultValue':'All hours'}, {'key':'leg','label':'Earlier trend length'}], 'Filter definitions')
                counts['context_rows'] += len(s['rows'])
                filtered_ids.append(s['id'])
        require(set(filtered_ids) == set(expected_filtered), 'Missing full metric tables')
        seen = set()
        for b in mapping['bindings']['numeric_projections']:
            sid,col = b['section'],b['column']; s=sections[sid]
            require(b['transform'] == 'blank_to_null_else_numeric_rounded_six_decimals', 'Projection transform')
            for i,line in b['row_pairs']:
                a = (sid,col,i)
                require(a in addresses and a not in seen, f'Address coverage {a}')
                seen.add(a)
                key,sc = expected_column(sid,col,i)
                rel=f'tables/pullback_{key}.csv'
                require(b['source'] == rel and b['source_column'] == sc and type(line) is int and 2 <= line <= len(tables[rel][1])+1, 'Source column binding')
                src=tables[rel][1][line-2]; dst=(s['items'] if s['kind']=='metrics' else s['rows'])[i]
                require(src['setting_ticks']==str(setting), 'Chart binding')
                require(dst[col] == numeric(src[sc]), f'Numeric differs {folder.name}/{a}')
                if 'rowFilters' in s:
                    require((dst['year'],dst['window'],dst['leg'])==(yl(src['year']),LABELS[src['timeframe_id']],ll(src['earlier_leg_bucket'])), 'Context binding')
                    require(src['direction'] == sid.rsplit('-',1)[1], 'Direction binding')
                    if sid.startswith('n'):
                        require(src['n'] == col[1:], 'Horizon binding')
                    if sid.startswith('depth-'):
                        require(src['level_percent']==sid.split('-')[1], 'Depth binding')
                    if sid.startswith('target-'):
                        require(src['target_multiple']==sid.split('-')[1][0] and src['horizon_candles']=='10', 'Target binding')
                else:
                    require(tuple(src[g] for g in ('year','timeframe_id','earlier_leg_bucket'))==('','all_hours','all'), 'Overall binding')
                    if s['kind'] == 'metrics':
                        require(src['direction'] == 'all', 'Coverage must use pooled directions')
                    if s['kind']=='table':
                        require(dst['direction']==DIRECTIONS[src['direction']], 'Overall direction label')
                        if sid.startswith('overall-') and sid!='overall-payoff':
                            require(src['direction']==sid[len('overall-'):] and src['n']==str(i+1), 'Overall n binding')
                        if sid=='overall':
                            require(src['direction']==tuple(DIRECTIONS)[i//4] and src['level_percent']==str((25,50,75,100)[i%4]), 'Overall depth binding')
                        if sid=='overall-payoff':
                            require(src['direction']==tuple(DIRECTIONS)[i//2] and src['target_multiple']==str(1+i%2), 'Overall target binding')
        require(seen == addresses and len(seen)==receipt['numeric_cells_checked'], 'All numeric cells covered')
        counts['numeric_cells']+=len(seen)
        bindings={x['download']:x for x in mapping['bindings']['downloads']}
        descriptors={Path(x['path']).name:x for x in report['downloads']}
        expected_downloads=set(PIVOTS) if view=='continuation' else {'retracement-recovery.csv','setup-samples.csv'} if view=='retracement' else {'gross-ohlc-payoff.csv','payoff-resolution.csv'}
        require(set(bindings)==set(descriptors)==expected_downloads, 'CSV allowlist')
        require({x.name for x in (folder/'downloads').iterdir()}==expected_downloads, 'CSV file inventory')
        for name in sorted(bindings):
            b=bindings[name];d=descriptors[name];rel=b['source']
            require(rel in tables and d['source']=={'runId':stage.name,'artifact':rel,'sha256':hashes[rel]}, 'Download attribution')
            selected=[(j+2,row) for j,row in enumerate(tables[rel][1]) if row['setting_ticks']==str(setting)]
            if view=='continuation':
                require(rel=='tables/pullback_continuation.csv' and b['source_column']==PIVOTS[name] and b['pivot_group']==list(GROUP)
                        and b['pivot_horizon']=='n' and b['setting_ticks']==setting, 'Pivot source')
                projection={}
                for _,row in selected:
                    k=tuple(row[g] for g in GROUP); out=projection.setdefault(k,dict(zip(GROUP,k)));out['n'+row['n']]=row[PIVOTS[name]]
                header=[*GROUP,*('n'+str(n) for n in range(1,21))];expected=list(projection.values())
            else:
                header=b['columns']
                table_name, expected_header = CSV_PROJECTIONS[name]
                require(rel == f'tables/pullback_{table_name}.csv' and header == expected_header, 'Explicit authored CSV projection')
                require(header==d['columns'] and len(header)<=24 and set(GROUP).issubset(header) and set(header).issubset(tables[rel][0]), 'Original projection header')
                require(b['source_rows']==[j for j,_ in selected], 'Original row bindings')
                expected=[{g:row[g] for g in header} for _,row in selected]
            h,actual=csv_read(folder/'downloads'/name)
            require(h==header==d['columns'] and actual==expected and len(actual)==d['rowCount'], 'Original strings/row count')
            require(sha(folder/'downloads'/name)==d['sha256']==b['sha256'], 'CSV checksum')
            counts['selected_csv_files']+=1;counts['selected_csv_rows']+=len(actual);counts['original_csv_cells']+=len(actual)*len(h)
        require(receipt['csv_files_checked']==len(bindings) and receipt['original_csv_strings_verified'], 'Producer CSV checks')
        if view == 'payoff':
            union = set().union(*(set(CSV_PROJECTIONS[name][1]) for name in expected_downloads))
            require(union == set(tables['tables/pullback_payoff.csv'][0]) - {'setting_ticks', 'units'}, 'Complete payoff field union across downloads')
        counts['publications']+=1
    for item in jl(prior):
        require(sha(root/item['path'])==item['sha256'], f'Prior publication changed {item["path"]}')
        counts['prior_publication_files']+=1
    hashes['publication-verification.json']=sha(stage/'publication-verification.json')
    for name,value in hashes.items():
        require(sha(stage/name)==value, 'Checked bytes changed')
    require(sha(script)==script_sha, 'Verifier changed')
    out={'schema_version':1,'result':'passed','run_id':stage.name,'checked_at':datetime.now(timezone.utc).isoformat(),'counts':counts,'artifact_hashes':hashes,'verifier':{'sha256':script_sha,'retained_path':snap.relative_to(stage).as_posix()},'scope':'Independent complete saved-table to report/context/original CSV transfer; no market reanalysis.'}
    with (vd/'publication-transfer-independent.json').open('x') as f:
        json.dump(out,f,indent=2,allow_nan=False);f.write('\n')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--prior',type=Path,required=True);a=p.parse_args()
    print(json.dumps(audit(a.stage.resolve(),a.workspace.resolve(),a.prior.resolve())['counts']))

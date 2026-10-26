#!/usr/bin/env python3
"""Package the supplied tracker evidence; never run market-data analysis."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
STUDY = '19_value_area_fade_tracker'
HERE = ROOT / 'studies' / STUDY
PUBLICATION = 'value-area-fade-tracker-20261007-source-review'
SOURCE_NAMES = ['post-55.txt', 'post-100.txt', *[f'chart-{i:02}.png' for i in range(1, 8)]]
FIGURE_TITLES = [
    '55 trades: overall, direction and grades',
    '55 trades: days, time blocks, VWAP and touches',
    '55 trades: shapes and ticker counts',
    '100 trades: overall, direction and grades',
    '100 trades: days, time blocks, VWAP and touches',
    '100 trades: shapes and ticker counts',
    '100 trades: streak summary and length distribution',
]
FIGURE_CAPTIONS = [
    'Source exhibit 1. Overall 71% wins, 27% losses, 2% break-even; long/short is trade mix, not directional win rate. Grade counts are 10/15/30. Separate grade win rates are not a composition.',
    'Source exhibit 2. Individual win rates are shown as pie slices; slice areas are not subgroup weights. Zero time-block labels do not supply denominators. Weekdays have the later post’s New Zealand caveat.',
    'Source exhibit 3. Ticker table supplies sample counts. MCL displays 0% with zero trades, so its rate is undefined. Shape/ticker rate slices are not shares of all wins.',
    'Source exhibit 4. Overall 69% wins, 29% losses, 2% break-even. Long/short is 49%/51% of trades. Grades have 22/35/43 observations.',
    'Source exhibit 5. Later chart reports VWAP 67%, first touch 78%, and 20:00–22:00 at 74%; subgroup counts are absent. The later text’s Asia preference is not an independently established best time.',
    'Source exhibit 6. Sample sizes are NQ 14, MNQ 24, ES 5, MES 18, GC 7, MGC 27, CL 4 and MCL 1. These are not paired micro/mini comparisons.',
    'Source exhibit 7. Two break-even trades are ignored and do not end a streak. The 98 included trades comprise 69 wins and 29 losses; longest observed streaks are six wins and three losses.',
]


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def ident(path, base=ROOT):
    return {'path': path.relative_to(base).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def publication_root():
    config = ROOT / 'config/paths.local.toml'
    if not config.exists():
        config = ROOT / 'config/paths.example.toml'
    settings = tomllib.loads(config.read_text())['paths']
    value = Path(os.environ.get('ABACUS_PUBLICATION_ROOT', settings['publication_root']))
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


def col(key, label, fmt=None):
    value = {'key': key, 'label': label}
    if fmt:
        value.update(format=fmt, precision=0)
    return value


def table(key, title, columns, rows, description, notes=()):
    return {'id': key, 'kind': 'table', 'title': title, 'columns': columns,
            'rows': rows, 'description': description, 'notes': list(notes)}


def text_section(key, title, body):
    return {'id': key, 'title': title, 'kind': 'text', 'body': body}


def report(run_id):
    sections = [text_section('evidence', 'What this study establishes',
        'Study 19 is an external source review of two user-supplied community posts and seven tracker screenshots. One trader reports every taken trade was logged: 55 cumulative trades over four weeks, then 100 over seven weeks. Browser headers attribute both posts to Christopher Thornton, with date labels Aug 5 and Aug 28 (edited); the year is not visible. We have no raw ledger or independently authenticated fills. These are overlapping cumulative samples, not 155 independent observations. Abacus has documented the source; our empirical analysis is planned for a future run.')]
    sections.append({'id': 'headline', 'kind': 'metrics', 'title': 'Reported snapshot sizes and latest win rate', 'items': [
        {'label': 'First snapshot', 'value': 55, 'format': 'number', 'unit': 'trades', 'note': 'Four weeks; included again in the later cumulative snapshot.'},
        {'label': 'Later snapshot', 'value': 100, 'format': 'number', 'unit': 'trades', 'note': 'Seven weeks; unaudited external tracking.'},
        {'label': 'Later reported wins', 'value': .69, 'format': 'percent', 'precision': 0, 'note': '69% of all 100 trades. P&L and costs were not supplied.'}]})
    sections.append(table('snapshots', 'Cumulative results and direction mix',
        [col('snapshot','Snapshot'),col('weeks','Weeks','number'),col('trades','Trades','number'),col('win','Wins','percent'),col('loss','Losses','percent'),col('breakeven','Break-even','percent'),col('long','Long mix','percent'),col('short','Short mix','percent')],
        [{'snapshot':'First','weeks':4,'trades':55,'win':.71,'loss':.27,'breakeven':.02,'long':.55,'short':.45},
         {'snapshot':'Later','weeks':7,'trades':100,'win':.69,'loss':.29,'breakeven':.02,'long':.49,'short':.51}],
        'Image 1 / post 1 and image 4 / post 2. Rates are the displayed rounded percentages.',
        ['Direction columns describe proportions of trades. No long-versus-short outcome rates are supplied.',
         'The first text calls direction almost evenly split; its chart shows 55% long and 45% short.',
         'Arithmetic reconciliation gives 39 wins, 15 losses and one break-even at 55; 69 wins, 29 losses and two break-evens at 100. The earlier counts are reconstructed from rounded percentages, not a supplied ledger.']))
    sections.append(text_section('strategy', 'Candidate strategy: first-touch value-area fade',
        'Strategy value_area_first_touch_fade · proposed · decision date 2026-10-07. In a balanced/rotational market, the source describes selling from value-area high (VAH) toward point of control (POC), or buying from value-area low (VAL) toward POC. Developing/current-session value areas, D-shaped profiles, early touches and VWAP are possible context variables. The first post reports 40 such fades among 55 trades, but no fade-only win rate; its overall rate cannot be assigned to this strategy. The author says they do not enter at POC. Later discussion separates balanced-day reversals from trending-day continuation. No operational continuation setup is provided, so that is a separate future branch. No Abacus trading or risk-increase recommendation follows from this source review.'))
    sections.append(table('rules', 'What is described, and what must be defined',
        [col('element','Element'),col('source','Source description'),col('gap','Required before testing')],
        [dict(element=a,source=b,gap=c) for a,b,c in [
            ('Market state','Balanced/rotational fades; trending continuation','A causal classifier and separate policies'),
            ('Profile','D-shape or clear volume building / acceptance','Volume resolution, shape metric and value-area percentage'),
            ('Levels','Developing/current VAH or VAL toward POC','Session reset, profile algorithm and level availability'),
            ('Touch','First/second contact favored','Tolerance, approach side, reset and deduplication'),
            ('VWAP','Additional confluence; later used for day context','Anchor, bands, proximity and context rule'),
            ('Grade','A/B/C quality grouping','An entry-time rubric independent of outcome; an author comment mentions generally three confluences with discretion'),
            ('Entry / stop','Wait for the setup; no POC entries','Trigger, timing, fill, stop, invalidation and timeout'),
            ('Exit','Initially 1:1; later let winners run','POC, fixed R and partial/runner policies separately'),
            ('Products','NQ/MNQ, ES/MES, GC/MGC, CL/MCL','Contract identity, rolls, fees, liquidity and position size')]],
        'Extracted descriptions are not complete executable rules. A final-session profile may not classify an earlier setup.'))
    sections.append(table('grades', 'Reported trade grades',
        [col('grade','Grade'),col('n55','N at 55','number'),col('rate55','Win rate at 55','percent'),col('n100','N at 100','number'),col('rate100','Win rate at 100','percent')],
        [dict(grade=g,n55=n1,rate55=r1,n100=n2,rate100=r2) for g,n1,r1,n2,r2 in [('A',10,1,22,.86),('B',15,.67,35,.69),('C',30,.63,43,.60)]],
        'Posts 1–2 and images 1 / 4. All rates are rounded source percentages.',
        ['Grade counts sum to 55 and 100. The grading rubric and when labels were assigned are unknown.',
         'A-grade 100% describes ten trades. Neither snapshot is a held-out test; increasing risk is the author’s suggestion, not a tested Abacus policy.']))
    filters=[('Profile','D-shape',.82,None,.80,None),('Profile','B-shape',.60,None,.60,None),('Profile','P-shape',.50,None,.50,None),('Profile','No real shape',.61,None,.56,None),
             ('Touch','First',.89,None,.78,None),('Touch','Second',.77,None,.71,None),('Touch','Third',.60,None,.58,None),('Touch','Fourth',.57,None,.63,None),('Touch','Fifth',.45,None,.56,None),('Confluence','VWAP',.81,16,.67,None)]
    sections.append(table('context','Profile, touch and VWAP observations',
        [col('group','Group'),col('label','Subgroup'),col('rate55','Win rate at 55','percent'),col('n55','N at 55','number'),col('rate100','Win rate at 100','percent'),col('n100','N at 100','number')],
        [dict(group=g,label=l,rate55=r1,n55=n1,rate100=r2,n100=n2) for g,l,r1,n1,r2,n2 in filters],
        'Posts 1–2 and images 2–3 / 5–6. Missing denominators display as Not available.',
        ['These are marginal groups, potentially overlapping. No combined A-grade + D-shape + first-touch + VWAP result is supplied.',
         'First/second-touch rates are higher in both snapshots; rates are not strictly decreasing at every later touch (fourth exceeds third at 100). This does not prove levels weaken causally.',
         'VWAP was introduced during tracking: 81% at N=16 becomes 67% at unspecified N. Selection and the later change in VWAP interpretation prevent an incremental-effect claim.',
         'Separate win rates are not shares of all wins. Source pie-slice areas are not appropriate comparisons.']))
    sections.append(table('tickers','Reported ticker results and sample counts',
        [col('ticker','Ticker'),col('n55','N at 55','number'),col('rate55','Win rate at 55','percent'),col('n100','N at 100','number'),col('rate100','Win rate at 100','percent')],
        [dict(ticker=t,n55=n1,rate55=r1,n100=n2,rate100=r2) for t,n1,r1,n2,r2 in [
            ('NQ',1,1,14,.79),('MNQ',11,.55,24,.63),('ES',2,0,5,.40),('MES',16,.81,18,.78),('GC',2,.50,7,.86),('MGC',20,.80,27,.67),('CL',3,.67,4,.75),('MCL',0,None,1,0)]],
        'Images 3 / 6 provide the full quantities; posts discuss selected tickers.',
        ['At 55, the source displays MCL 0% with N=0; its rate is normalized here to unavailable. At 100, MCL 0% has N=1 and is a reported observed rate.',
         'Small groups, including NQ N=1 and GC N=2 at 55, cannot establish stable ticker rankings.',
         'The author later trades more minis and reports partial fills in micros. This is not a matched micro-versus-mini comparison.']))
    sections.append(table('days','Weekday labels as reported',
        [col('label','Source weekday label'),col('rate55','Win rate at 55','percent'),col('rate100','Win rate at 100','percent')],
        [dict(label=d,rate55=a,rate100=b) for d,a,b in [('Monday',.75,.85),('Tuesday',.60,.56),('Wednesday',.90,.92),('Thursday',.64,.68),('Friday',.69,.64)]],
        'Images 2 / 5. The later post says these are New Zealand weekdays: its Monday/Wednesday correspond to New York Sunday/Tuesday sessions.',
        ['Subgroup counts and dated timestamps are absent. Do not use these rows as New York exchange weekday filters.',
         'The author has more time to focus on Wednesday, a possible availability confound. The first post’s weekday convention was not explicitly defined.']))
    times=[('00:00–02:00',.90,10,'90%',.65,None,'65%'),('02:00–04:00',.60,None,'60%',.67,None,'67%'),
           *[(f'{a:02}:00–{a+2:02}:00',None,None,'0%',None,None,'0%') for a in range(4,14,2)],
           ('14:00–16:00',None,None,'0%',.50,None,'50%'),('16:00–18:00',None,None,'0%',None,None,'0%'),
           ('18:00–20:00',.76,21,'76%',.68,None,'68%'),('20:00–22:00',.64,None,'64%',.74,None,'74%'),('22:00–00:00',.40,None,'40%',.70,None,'70%')]
    sections.append(table('timeblocks','Time blocks labeled New York time',
        [col('block','NY time block'),col('rate55','Win rate at 55','percent'),col('n55','N at 55','number'),col('display55','Original label at 55'),col('rate100','Win rate at 100','percent'),col('n100','N at 100','number'),col('display100','Original label at 100')],
        [dict(block=t,rate55=a,n55=na,display55=da,rate100=b,n100=nb,display100=db) for t,a,na,da,b,nb,db in times],
        'Images 2 / 5; post 1 supplies N=10 at 00:00–02:00 and N=21 at 18:00–20:00.',
        ['A displayed 0% with unspecified N cannot distinguish no trades from zero wins. Normalized rates are unavailable; original labels are preserved.',
         'The source favors Asia trading, but descriptions change from the hour leading into Asia open to about an hour after the market opens. Exact session boundaries are undefined.',
         'At 100 the largest nonzero time-block rate shown is 74% at 20:00–22:00, not 18:00–20:00 (68%). Missing counts prevent a reliable best-time ranking.',
         'Future analysis must use dated UTC timestamps, America/New_York DST and explicit exchange/session dates.']))
    sections.append(table('streaksummary','Reported streak summary at 100 trades',
        [col('type','Streak type'),col('count','Streaks','number'),col('longest','Longest','number'),col('current','Current','number'),{'key':'average','label':'Reported average length','format':'number','precision':1},col('trades','Trades in streaks','number')],
        [dict(type='Win',count=22,longest=6,current=1,average=3.1,trades=69),dict(type='Loss',count=21,longest=3,current=0,average=1.4,trades=29)],
        'Image 7. Total: 43 streaks, 98 included trades, reported average 2.3; latest result is a win.',
        ['Two break-even trades are ignored and do not end a streak. This convention affects streak counts.',
         'The sequence itself is unavailable. No independent sequence check, simulation or future losing-streak forecast is established.']))
    sections.append(table('streaklength','Reported streak-length distribution',
        [col('length','Length','number'),col('wins','Win streaks','number'),col('losses','Loss streaks','number')],
        [dict(length=l,wins=w,losses=x) for l,w,x in [(1,3,14),(2,7,6),(3,4,1),(4,3,0),(5,2,0),(6,3,0)]],
        'Image 7. Quantities reconcile to 22 win streaks / 69 wins and 21 loss streaks / 29 losses.'))
    sections.append(text_section('opposing','Negative and inconclusive source claims',
        'The author reports no support for the idea that same-type aligned value areas (for example current VAH aligning with prior or overnight VAH) improve success relative to unlike-type alignment. No sample counts, effect estimate or exact comparison rule were provided. Preserve this as a negative external claim, not a controlled Abacus rejection. The later VWAP rate falls to 67%, and A-grade falls to 86%; high early rates did not persist unchanged. The source’s direction-neutrality conclusion lacks direction-specific outcome rates. D-shape, first-touch and grade associations have unspecified confounding and no joint-filter data.'))
    sections.append(text_section('management','Trade management and execution limits',
        'Post 1 describes standardizing trades at 1:1 R:R. Post 2 says letting winners run improved profitability despite lower win rate; it reports an average 1:2 R:R for the last eight A-grade trades and suggests partial profits at 1:1 with a runner. These are the author’s descriptions, not verified realized returns or a tested exit comparison. A follow-up author comment says they only trade 1:1 and tracked how far A grades would run, so the 1:2 figure may describe potential excursion rather than realized payoff. There is no payoff series, mean win/loss, fees, slippage, sizing or P&L amounts. Reported partial fills in micros matter for capacity. A 69% win rate cannot establish positive net expectancy, nor does the streak summary justify increasing risk. Psychological comments describe the author’s experience; they are not statistical proof of a coin-flip process.'))
    sections.append(text_section('future','Planned Abacus extension',
        'Future work will first obtain a raw timestamped ledger if available and define reproducible causal profiles, balanced/trending state, D-shape, touch counting, grade and VWAP rules before outcome inspection. Pin immutable Bhishma releases and available_at timing. Prespecify chronological development and untouched holdout periods. Compare first-touch balanced VA fades with later-touch opportunities under the same execution policy, then assess shape and VWAP separately; report coverage and retain negative findings. Freeze entry/fill, stop, timeout, POC/fixed-R/partial-runner exits, unadjusted prices, costs, contract rolls and overlapping-position treatment. Report net R, drawdown, MFE/MAE and session-clustered uncertainty, with all missing/ambiguous events retained. Separate discretionary taken-trade audits from all-eligible market-event research. Our own analysis has not been run.'))
    sections.append(table('ledger','Fields to collect for our future analysis',
        [col('field','Field group'),col('purpose','Purpose')],
        [dict(field=a,purpose=b) for a,b in [
            ('Identity','Trade/event ID, contract, instrument, strategy branch and rule version'),
            ('Time','UTC signal/order/fill/exit; IANA timezone, exchange trade date, session'),
            ('Causal levels','VAH/VAL/POC and available_at; profile algorithm, window and value percentage'),
            ('Context','Shape, balanced/trending state, VWAP/anchor; exact values at signal'),
            ('Touch / grade','Pre-entry touch count/reset/tolerance and frozen grade rubric'),
            ('Orders / fills','Submitted/filled size, order type, partial fills, cancellations and liquidity'),
            ('Risk / exit','Initial stop/risk, target, exit policy, partial/runner fills and timeout'),
            ('Payoff','Unadjusted prices, fees/slippage, realized net R, MFE/MAE and ambiguity'),
            ('Selection','All eligible opportunities, exclusion reason, taken/skipped and trader availability')]],
        'Collection plan only; these fields were not supplied in the external summaries.'))
    sections.append(text_section('limitations','Interpretation limits',
        'One trader, a short evolving seven-week process, self-selected opportunities, overlapping groups and cumulative samples. Grades may be retrospective; many denominators and all individual timestamps are missing. We cannot estimate joint-filter performance, incremental VWAP benefit, a weekday edge, fill capacity, drawdown or net profitability. Rounded percentages and arithmetic consistency do not authenticate the record. Changes in market mix, exits and the author’s skill prevent attributing changes to one filter. The screenshots’ rate pies should be read as labeled values rather than valid shares of a whole.'))
    sections.append(text_section('sources','Source and preservation record',
        'Two pasted posts and seven supplied screenshots were reviewed on 2026-10-07. The first post is linked by the later post; its webpage was not retrievable with the web tool. Existing signed-in browser tabs confirmed Christopher Thornton as author, the follow-up URL, and date labels Aug 5 / Aug 28 (edited). No year was visible. Selected author comments clarify discretionary grading and uncertainty over realized versus potential R:R. Cam Narayan is acknowledged as a teacher, not the author. Full post bytes are retained privately with checksums. Selected screenshots are preserved without editing, and public tables/downloads are transferred from the saved source-review tables. The completed review has frozen settings, input hashes, source/environment identities and an integrity manifest. New analysis or interpretation requires a new run.'))
    sections[-1]['referenceIds']=['first-post','follow-up']
    for i,(title,caption) in enumerate(zip(FIGURE_TITLES,FIGURE_CAPTIONS),1):
        sections.append({'id':f'exhibit-{i}', 'kind':'figure','title':title,
                         'path':f'figures/chart-{i:02}.png','alt':f'Original supplied tracker screenshot: {title}. Transcribed values and limitations appear in the report tables.', 'caption':caption})
    return {'schemaVersion':'1.1','id':PUBLICATION,'title':'Value-area fade tracker: 55 to 100 reported trades',
            'summary':'An external evidence study and proposed first-touch VAH/VAL-to-POC strategy. Two overlapping snapshots, seven source charts, reported rates and sample counts, contrary evidence, execution gaps and a plan for future independent Abacus analysis.',
            'publishedAt':now(),'source':{'producer':'sahadeva','runId':run_id},'sections':sections,
            'notes':['Source review completed; independent analysis planned. No Abacus backtest or verified profitability.',
                     'The first 55 trades are included in the 100. Missing values stay unavailable; percentages are rounded source labels.'],
            'references':[{'id':'first-post','kind':'external','label':'First tracker post (linked in supplied follow-up)','title':'Trading Stats - Tracked Results','creator':'Christopher Thornton','url':'https://www.skool.com/volumeprofile/trading-stats-tracked-results?p=6c7c7fc7','accessedOn':'2026-10-07'}, {'id':'follow-up','kind':'external','label':'100-trade follow-up','title':'Trading Stats - Tracked Results (100 Trades)','creator':'Christopher Thornton','url':'https://www.skool.com/volumeprofile/trading-stats-tracked-results-100-trades?p=fcadc280','accessedOn':'2026-10-07'}]}


def write_csv(path, section):
    buffer=io.StringIO(newline=''); keys=[c['key'] for c in section['columns']]
    writer=csv.DictWriter(buffer,fieldnames=keys,lineterminator='\n');writer.writeheader()
    writer.writerows({k:'' if r[k] is None else r[k] for k in keys} for r in section['rows'])
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(buffer.getvalue(),encoding='utf-8')


def render(rep,bundle):
    md=[f'# {rep["title"]}', '',rep['summary'],'']; html=[]
    for s in rep['sections']:
        md.extend([f'## {s["title"]}','']);html.append(f'<section id="{s["id"]}"><h2>{escape(s["title"])}</h2>')
        if s['kind']=='text': md.extend([s['body'],'']);html.append(f'<p>{escape(s["body"])}</p>')
        elif s['kind']=='figure':
            md.extend([f'![{s["alt"]}]({s["path"]})','',s.get('caption',''),''])
            html.append(f'<figure><a href="{s["path"]}"><img src="{s["path"]}" alt="{escape(s["alt"],quote=True)}"></a><figcaption>{escape(s.get("caption",""))}</figcaption></figure>')
        elif s['kind']=='metrics':
            for item in s['items']:
                value=f'{item["value"]*100:.0f}%' if item['format']=='percent' else str(item['value'])
                md.extend([f'- {item["label"]}: {value}. {item.get("note","")}'])
                html.append(f'<p><strong>{escape(item["label"])}: {value}</strong> {escape(item.get("note",""))}</p>')
            md.append('')
        else:
            def display(row,c):
                value=row[c['key']]
                if value is None:return 'Not available'
                return f'{value*100:.0f}%' if c.get('format')=='percent' else str(value)
            md.extend([s['description'],'','| '+' | '.join(c['label'] for c in s['columns'])+' |','| '+' | '.join('---' for _ in s['columns'])+' |'])
            md.extend('| '+' | '.join(display(r,c) for c in s['columns'])+' |' for r in s['rows']);md.append('')
            html.append(f'<p>{escape(s["description"])}</p><div class="table" tabindex="0"><table><thead><tr>'+''.join(f'<th>{escape(c["label"])}</th>' for c in s['columns'])+'</tr></thead><tbody>')
            html.extend('<tr>'+''.join(f'<td>{escape(display(r,c))}</td>' for c in s['columns'])+'</tr>' for r in s['rows']);html.append('</tbody></table></div>')
            for note in s.get('notes',[]):md.extend([f'- {note}']);html.append(f'<p class="note">{escape(note)}</p>')
            md.append('')
        html.append('</section>')
    md.extend(['## Source link','',f'[First tracker post]({rep["references"][0]["url"]})',''])
    (bundle/'report.md').write_text('\n'.join(md),encoding='utf-8')
    css='body{font:17px/1.6 system-ui;max-width:1080px;margin:auto;padding:32px;color:#18324b}h1{font-size:2.5rem}section{margin:42px 0}img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%}th,td{padding:9px;border:1px solid #ccd5dd;text-align:left;vertical-align:top}th{background:#edf2f6}.table{overflow:auto}.note,figcaption{font-size:14px;color:#4b5c6d}'
    (bundle/'report.html').write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(rep["title"])}</title><style>{css}</style></head><body><h1>{escape(rep["title"])}</h1><p>{escape(rep["summary"])}</p>'+''.join(html)+f'<p><a href="{rep["references"][0]["url"]}">First tracker post</a></p></body></html>',encoding='utf-8')


def verify(bundle, check_manifest=True):
    rep=load(bundle/'publication.json'); metrics=load(bundle/'metrics.json');locked=load(bundle/'inputs.lock.json')
    for source in locked['sources']:
        assert sha(publication_root()/source['path'])==source['sha256'],source['id']
    tables={s['id']:s for s in rep['sections'] if s['kind']=='table'}
    assert metrics['tables']==tables,'Saved tables differ from publication'
    for section in tables.values():
        expected=io.StringIO(newline='');keys=[c['key'] for c in section['columns']]
        w=csv.DictWriter(expected,fieldnames=keys,lineterminator='\n');w.writeheader()
        w.writerows({k:'' if r[k] is None else r[k] for k in keys} for r in section['rows'])
        assert (bundle/'tables'/f'{section["id"]}.csv').read_text()==expected.getvalue()
    for key in ['grades','tickers']:
        assert sum(r['n55'] for r in tables[key]['rows'])==55
        assert sum(r['n100'] for r in tables[key]['rows'])==100
    assert tables['tickers']['rows'][-1]['rate55'] is None
    assert tables['tickers']['rows'][-1]['rate100']==0
    for key in ['grades','tickers']:
        sums=[]
        for suffix in ['55','100']:
            wins=[]
            for r in tables[key]['rows']:
                n=r[f'n{suffix}'];rate=r[f'rate{suffix}']
                if n==0:continue
                candidates=[w for w in range(n+1) if abs(w/n-rate)<.005000001]
                assert len(candidates)==1,(key,r,candidates)
                wins.extend(candidates)
            sums.append(sum(wins))
        assert sums==[39,69],(key,sums)
    lengths=tables['streaklength']['rows']
    assert sum(r['wins'] for r in lengths)==22 and sum(r['losses'] for r in lengths)==21
    assert sum(r['length']*r['wins'] for r in lengths)==69
    assert sum(r['length']*r['losses'] for r in lengths)==29
    for s in rep['sections']:
        if s['kind']=='figure':
            source=next(x for x in locked['sources'] if x['id']==Path(s['path']).stem)
            assert sha(bundle/s['path'])==source['sha256']
    for d in rep['downloads']:
        assert sha(bundle/d['path'])==d['sha256']==sha(bundle/d['source']['artifact'])
        assert (bundle/d['path']).read_bytes()==(bundle/d['source']['artifact']).read_bytes()
    if check_manifest:
        for item in load(bundle/'manifest.json')['artifacts']:
            assert sha(bundle/item['path'])==item['sha256'],item['path']
    return {'result':'passed','checked_at_utc':now(),'checks':['ten exact retained input/observation hashes','ten table transfers from saved metrics','grade and ticker totals / rounded-rate reconciliation','streak quantities and lengths','undefined versus zero rates','seven unedited figure hashes','four byte-identical summary CSV downloads','artifact inventory' if check_manifest else 'artifact inventory follows finalization'],
            'source_review':'all two posts and seven supplied screenshots visually reviewed; original authorship/ledger not authenticated','limitation':'Integrity and transcription checks, not empirical or profitability validation.'}


def prepare(run_id):
    dest=ROOT/'work'/STUDY/run_id;dest.mkdir(parents=True,exist_ok=False)
    locked=load(HERE/'inputs.lock.json');dump(dest/'inputs.lock.json',locked)
    for name in SOURCE_NAMES[2:]:
        source=next(x for x in locked['sources'] if x['id']==Path(name).stem)
        (dest/'figures').mkdir(exist_ok=True);shutil.copyfile(publication_root()/source['path'],dest/'figures'/name)
    rep=report(run_id)
    tables={s['id']:s for s in rep['sections'] if s['kind']=='table'}
    dump(dest/'metrics.json',{'evidence_kind':'reported_external_aggregates','independent_empirical_results':False,'units':'percent fields are ratios; counts are trades/streaks; unknown denominators null','uncertainty':'not estimated; dependence and missing denominators prevent validation','cohort':'two overlapping cumulative snapshots of one trader','tables':tables})
    for section in tables.values():write_csv(dest/'tables'/f'{section["id"]}.csv',section)
    rep['downloads']=[]
    for key in ['grades','tickers','context','timeblocks']:
        s=tables[key];path=dest/'tables'/f'{key}.csv';out=dest/'downloads'/f'{key}.csv';out.parent.mkdir(exist_ok=True);shutil.copyfile(path,out)
        rep['downloads'].append({'id':key,'path':f'downloads/{key}.csv','label':s['title'],'description':s['description'],
            'population':'One external trader; cumulative 55- and 100-trade snapshots, overlapping and unaudited.',
            'units':'Win rates are ratios (0.69 = 69%); N is trade count. Blank means unavailable, not zero.',
            'scope':'All rows and columns of this selected summary table; no individual trade ledger.',
            'mediaType':'text/csv','sha256':sha(out),'rowCount':len(s['rows']),'columns':[c['key'] for c in s['columns']],
            'source':{'runId':run_id,'artifact':f'tables/{key}.csv','sha256':sha(path)}})
    dump(dest/'publication.json',rep);render(rep,dest)
    dump(dest/'config.json',{'study_id':STUDY,'run_id':run_id,'protocol_version':'1.0.0','type':'external_source_documentation','source_selection':'two supplied posts and all seven screenshots','exclusions':'no fabricated ledger, market data, P&L, missing denominators or joint-filter estimates','strategy_status':'proposed','future_analysis':'not run','break_even_streak_rule':'ignored and does not end a streak (source image 7)','publication_prepared_before_seal':True})
    (dest/'advice.md').write_text((ROOT/'strategies/value_area_first_touch_fade.md').read_text().replace('../studies/', '../../../studies/'), encoding='utf-8')
    source_dir=dest/'provenance/study-source';source_dir.mkdir(parents=True)
    for file in HERE.iterdir():
        if file.is_file():shutil.copyfile(file,source_dir/file.name)
    shutil.copyfile(ROOT/'uv.lock',dest/'provenance/uv.lock')
    shutil.copyfile(ROOT/'apps/narada/package-lock.json',dest/'provenance/narada-package-lock.json')
    (dest/'provenance/python-version.txt').write_text(sys.version+'\n')
    (dest/'provenance/git-status.txt').write_text(subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True))
    checks=verify(dest,False);dump(dest/'verification.json',checks)
    manifest={'schema_version':'source-review-run-1','study_id':STUDY,'run_id':run_id,'completed_at_utc':now(),
        'evidence_kind':'external_source_review','code_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'dirty_source_snapshot':'provenance/study-source','environment':{'python':sys.version,'uv_lock_sha256':sha(ROOT/'uv.lock'),'narada_npm_lock_sha256':sha(ROOT/'apps/narada/package-lock.json')},
        'commands':[f'.venv/bin/python studies/{STUDY}/document.py prepare --run-id {run_id}',f'.venv/bin/python studies/{STUDY}/document.py verify --bundle work/{STUDY}/{run_id}',f'.venv/bin/python studies/{STUDY}/document.py seal --run-id {run_id}'],
        'inputs':locked['sources'],'checks':checks,'large_evidence':'No market events; nine exact supplied source files plus browser attribution observations retained privately via input lock. No off-device backup verified.',
        'artifacts':[ident(p,dest) for p in sorted(dest.rglob('*')) if p.is_file()]}
    dump(dest/'manifest.json',manifest);verify(dest);print(dest.relative_to(ROOT))


def export(run_id, revision):
    source=ROOT/'runs'/STUDY/run_id;verify(source)
    dest=ROOT/'reports/exports'/STUDY/run_id/revision;dest.mkdir(parents=True,exist_ok=False)
    for name in ['publication.json','figures','downloads']:
        if (source/name).is_dir():shutil.copytree(source/name,dest/name)
        else:shutil.copyfile(source/name,dest/name)
    original=load(source/'publication.json');rep=load(source/'publication.json')
    corrections=[]
    if rep['source']['producer'] != 'sahadeva':
        corrections=[{'field':'source.producer','before':rep['source']['producer'],'after':'sahadeva'},
                     {'field':'id','before':rep['id'],'after':rep['id']+'-r2'}]
        rep['source']['producer']='sahadeva';rep['id'] += '-r2'
        dump(dest/'publication.json',rep)
    section_maps=[]
    for s in rep['sections']:
        if s['kind']=='table':
            section_maps.append({'section':s['id'],'artifact':f'tables/{s["id"]}.csv','sha256':sha(source/'tables'/f'{s["id"]}.csv'),
                'selector':'all rows, ordered columns; exact saved cells','cells':[{'row':i,'column':c['key'],'value':r[c['key']]} for i,r in enumerate(s['rows']) for c in s['columns']]})
        else:section_maps.append({'section':s['id'],'artifact':'publication.json','selector':f'sections[id={s["id"]}] copied unchanged','sha256':sha(source/'publication.json')})
    dump(dest/'source-map.json',{'source_run_id':run_id,'metadata_corrections':corrections,'sections':section_maps,'downloads':[{'path':d['path'],'artifact':d['source']['artifact'],'selector':'all rows and columns; exact byte copy','sha256':d['sha256']} for d in rep['downloads']]})
    for d in rep['downloads']:assert (dest/d['path']).read_bytes()==(source/d['source']['artifact']).read_bytes()
    assert load(dest/'publication.json')==rep and rep['sections']==original['sections']
    dump(dest/'verification.json',{'result':'passed','at':now(),'checks':['source run integrity','all source sections retained without numerical or interpretive change','canonical producer metadata and new ID correction recorded' if corrections else 'source publication unchanged','all table cell maps derived from the same saved report/tables','all selected figures unchanged','four full-table downloads byte-identical to saved CSVs'],'limitation':'Publisher and release/browser gates follow separately; no market-data analysis.'})
    (dest/'document-source.py').write_bytes(Path(__file__).read_bytes())
    dump(dest/'manifest.json',{'study_id':STUDY,'source_run_id':run_id,'revision_id':revision,'publication_id':rep['id'],'created_at_utc':now(),
        'change':'Presentation-only staging; canonical producer metadata corrected under a new publication ID when needed. Source sections and meaning unchanged.',
        'renderer':'study-specific document.py 1.0.0; Narada source contract 1.1',
        'command':f'.venv/bin/python studies/{STUDY}/document.py export --run-id {run_id} --revision-id {revision}',
        'source_artifacts':[ident(p) for p in sorted(source.rglob('*')) if p.is_file()],
        'outputs':[ident(p) for p in sorted(dest.rglob('*')) if p.is_file()]})
    print(dest.relative_to(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','verify','seal','export']);parser.add_argument('--run-id');parser.add_argument('--bundle',type=Path);parser.add_argument('--revision-id');args=parser.parse_args()
    if args.action=='verify':
        assert args.bundle;print(json.dumps(verify(args.bundle.resolve()),indent=2));return
    assert args.run_id and re.fullmatch(r'[A-Za-z0-9_-]+',args.run_id)
    if args.action=='prepare':prepare(args.run_id)
    elif args.action=='seal':
        source=ROOT/'work'/STUDY/args.run_id;verify(source);dest=ROOT/'runs'/STUDY/args.run_id
        assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(source,dest);print(dest.relative_to(ROOT))
    else:
        assert args.revision_id and re.fullmatch(r'[A-Za-z0-9_-]+',args.revision_id);export(args.run_id,args.revision_id)


if __name__=='__main__':main()

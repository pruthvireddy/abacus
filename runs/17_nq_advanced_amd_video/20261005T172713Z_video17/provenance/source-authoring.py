from pathlib import Path
import csv, hashlib, json, shutil
R=Path.cwd()
S='17_nq_advanced_amd_video'
W=R/'work'/S
W.joinpath('tables').mkdir(exist_ok=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def table(name,fields,rows):
    with (W/'tables'/name).open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(fields);writer.writerows(rows)
transcript_input=Path('/var/folders/8m/7y_qdqcn1fn6gkf6ggc_39bc0000gn/T/browser-use/exports/youtube-mmem9CI7vvw-7c48911a-5866-435d-a819-49f4d4982d67.txt')
retained=R/'data/research/sahadeva'/S/'sources/mmem9CI7vvw/20261005'
retained.mkdir(parents=True,exist_ok=True)
transcript=retained/'transcript.en.auto.txt'
if transcript.exists():
    assert sha(transcript)==sha(transcript_input)
else: shutil.copy2(transcript_input,transcript)
source={'video_id':'mmem9CI7vvw','url':'https://www.youtube.com/watch?v=mmem9CI7vvw','user_url':'https://www.youtube.com/watch?v=mmem9CI7vvw&t=16s','title':'The COMPLETE advanced AMD masterclass (FULL model guide)','creator':'Tmac','channel':'https://www.youtube.com/@tmacfutures','publication_date_as_displayed':'2026-10-05','access_date':'2026-10-05','duration_seconds':1631.401,'displayed_duration':'27:11','reviewed_from_seconds':0,'caption_language':'en','caption_type':'auto-generated','chart_period':{'start':'2026-09-28','end':'2026-10-02','basis':'Visible day/date labels in the charts; distinct from publication date.'},'chart_clock_note':'UTC+4 visible in several source chart status bars; no assumption that chart clock is New York time.','video_downloaded':False,'private_forecast_authentication':'not_verified','quarterly_claim_validation':'not_performed'}
dump(W/'source.json',source)
lock={'schema_version':'external-source-lock-1','study_id':S,'publication_root_resolution':'config/paths.local.toml [paths].publication_root = .; explicit --publication-root . used for this run','sources':[{'kind':'youtube_video','video_id':source['video_id'],'url':source['url'],'access_date':source['access_date'],'transcript':{'path':transcript.relative_to(R).as_posix(),'root_alias':'publication_root','sha256':sha(transcript),'bytes':transcript.stat().st_size,'retention':'retained ignored research storage; separate backup required','language':'en','captions':'auto-generated','acquisition':'connected browser content.exportYouTubeTranscript()'}}],'market_datasets':[]}
dump(R/'studies'/S/'inputs.lock.json',lock)
dump(W/'config.json',{'study_id':S,'protocol_version':'1.0.0','review_type':'qualitative_source_review','review_interval_seconds':[0,1631.401],'user_link_offset_seconds':16,'screenshots':14,'screenshot_selection':'purposive coverage of core explanations, preferred/weak entries, abstention, hypothesis revision and target shortfall','comparisons':'qualitative only; no inferential statistics','exclusions':['full-video duplication','market-data backtest','verification of private-message posting times','inferred trade fills or net profitability','public publication'],'execution_assumptions':None,'train_validation_test_split':None,'prior_inspection':'Source and captions inspected before exploratory review protocol was written','uncertainties':['automatic-caption specialist terms','external swing/OB/BOS definitions','session timing','quarterly event definition','news execution and costs'],'template_version':'amd-source-review-html-1'})
captures=json.loads((W/'capture-log.json').read_text())
annotations=[
('H1','Weekly-zone context','Broader rebound and an annotated continuation thesis.','Thesis illustration; not a probabilistic forecast.'),
('M5','Monday external sweep','Marked Monday low and the later weekly path.','Retrospective chart already contains later outcomes.'),
('3M','Quarterly candle argument','Three-month chart used to motivate bullish context.','Does not enumerate or verify all quarters since 1999.'),
('M3','Tuesday retest','Mini-cycle returns to the earlier zone before expansion.','Source session names retained; exact clock rules unresolved.'),
('M3','Tuesday alternatives','Several local reactions inside an upward session.','Alternatives are dependent opportunities, not independent verified trades.'),
('M3','Wednesday OB chain','First reaction, structure break and subsequent zone.','Second-zone preference depends on intervening information.'),
('M1','Wednesday weak re-entry','Repeated interactions near the New York entry area.','No mechanical maximum retest count supplied.'),
('M5','Wednesday later sweep','Replay cut at a downside sweep with projected continuation.','Drawn continuation lines are projections, not observed prices.'),
('M5','Thursday abstention','Overlapping swings and competing nearby structures.','No-position statement is speaker reported, not account audited.'),
('M5','Friday prior short hypothesis','Upper area and later price action while short thesis is discussed.','The screenshot is retrospective; it does not authenticate prior intent.'),
('M3','Friday news expansion','Sharp upward leg followed by retracement and overlap.','News identity follows speaker; independent release reconstruction excluded.'),
('M1','Friday confirmation entry','Sweep and later zone after the reaction.','No exact executable fill reconstructed.'),
('H1','Friday target shortfall','Nearer hourly draw and broader objective above.','All-time-high objective remained unmet in the video week.'),
('M15','Weekly overview','Whole-week path with linked zones across sessions.','Later bars are visible; cannot use as real-time feature input.')]
rows=[]
for c,(tf,title,observation,limit) in zip(captures,annotations):
    t=c['seconds']; f='figures/'+c['file']; p=W/f
    rows.append([c['file'][:2],t,f'{t//60}:{t%60:02d}',f'https://www.youtube.com/watch?v=mmem9CI7vvw&t={t}s',f,tf,title,observation,limit,sha(p),p.stat().st_size,'visually inspected'])
table('charts.csv',['chart_id','seconds','timestamp','source_url','file','displayed_timeframe','subject','visible_observation','interpretive_limit','sha256','bytes','review_status'],rows)
coverage=[
(0,93,'Purpose and promotional prediction claim','Higher-timeframe framework and selected earlier clips are promised.'),
(93,142,'Monday embedded clip','Speaker frames an early low-of-week hypothesis and Asia confirmation alternatives.'),
(142,238,'Higher-timeframe context','Weekly-zone reaction and hourly reaccumulation motivate bullish direction.'),
(238,368,'Countertrend Monday sequences','Speaker distinguishes possible shorts from preferred bias-aligned participation.'),
(368,466,'Monday sweep and entry choice','External low sweep; reaction/BOS; aggressive entry declined by speaker.'),
(466,555,'Quarterly argument','Three-month-candle historical assertion and low-of-week reasoning; unverified.'),
(555,690,'Tuesday zone retest','AMD Asia versus direct distributive Asia; prior-zone context.'),
(690,802,'Tuesday entry alternatives','Reported point/R opportunities; zones carry forward into Wednesday.'),
(802,842,'Embedded Wednesday setup discussion','Equal lows and a further sweep/continuation scenario; original posting time unverified.'),
(842,972,'Wednesday order-block chain','Preference for reaction/BOS-confirmed later zone; alternative targets.'),
(972,1020,'Wednesday weak New York entry','Repeated mitigation makes nominally valid re-entry less attractive.'),
(1020,1156,'Wednesday continuation','Higher-timeframe bullish context and later external sweep; patient entry alternatives.'),
(1156,1263,'Thursday no-trade','Awkward overlap, weak destinations and rejected alternatives.'),
(1263,1404,'Friday thesis revision','Range/short hypothesis revised after upward news response.'),
(1404,1467,'Friday local execution','One-minute exception; first-touch versus confirmation and retest.'),
(1467,1497,'Target reconciliation','ATH unmet; nearer hourly highs identified; next-week idea untested.'),
(1497,1588,'Weekly synthesis','Carry context from day to day; intraday entry detail intentionally incomplete.'),
(1588,1631.401,'Closing promotion and end','Mentorship/Discord promotion excluded from research recommendations.')]
table('coverage.csv',['start_seconds','end_seconds','topic','review_note'],coverage)
claims=[
('C01',0,48,'Perfectly predicted all moves','presenter_performance_claim','not_independently_verified','Edited examples and clips are not a complete timestamped forecast or trade record.'),
('C02',153,238,'Weekly-zone reaction supports bullish direction','presenter_interpretation','illustrated_not_tested','Chart 01; a contextual thesis, not a calibrated probability.'),
('C03',238,368,'Countertrend short opportunities can be passed','presenter_decision','reported','A direction filter does not prove shorts lack positive expectancy.'),
('C04',368,466,'Monday sweep establishes candidate weekly low','presenter_interpretation','illustrated_hindsight_sensitive','Chart 02; weekly-low status is known only after subsequent days.'),
('C05',428,447,'Speaker did not take aggressive Monday entry','presenter_trade_claim','not_account_verified','Distinguish a forecast or opportunity from an executed trade.'),
('C06',466,555,'Quarterly inside-candle event never occurred since 1999','historical_universal_claim','unverified_ambiguous_definition','Chart 03; inside-range versus close-in-range and data construction unresolved.'),
('C07',634,668,'Asia confirmation may be direct expansion or a mini AMD cycle','presenter_pattern_taxonomy','illustrated_not_tested','Chart 04; alternative qualitative conditions.'),
('C08',690,697,'Earlier Tuesday opportunity approximately 320 points and 7R','presenter_example_magnitude','unaudited','No independently reconciled fills, costs or complete stop/exit assumptions.'),
('C09',722,735,'Tuesday alternatives approximately 140 and 134 points','presenter_example_magnitude','unaudited','Chart 05; overlapping context and alternative participation.'),
('C10',774,799,'A confirmed Tuesday zone informs Wednesday','presenter_interpretation','illustrated_not_tested','Cross-day context; zone availability must be recorded causally.'),
('C11',854,950,'Later Wednesday OB preferable after reaction and BOS','presenter_entry_preference','illustrated_not_tested','Chart 06; reason is confirmation, not ordinal zone numbering.'),
('C12',972,1017,'Repeated mitigation weakens Wednesday re-entry','presenter_quality_filter','subjective_unquantified','Chart 07; no retest-count cutoff supplied.'),
('C13',1077,1110,'Later external sweep gives cleaner continuation setup','presenter_interpretation','illustrated_not_tested','Chart 08; replay projections distinguished from realized bars.'),
('C14',1156,1263,'No acceptable Thursday position','presenter_abstention_claim','reported_not_account_verified','Chart 09; retains a rejected day rather than only preferred entries.'),
('C15',1263,1404,'Friday upward news response overturns short/range idea','presenter_thesis_revision','retrospective_explanation','Charts 10 and 11; reaction to observed response is not advance news prediction.'),
('C16',1404,1464,'Friday one-minute BOS/retest entry preferred','presenter_entry_preference','illustrated_not_tested','Chart 12; timeframe flexibility and missed-retest cost not evaluated.'),
('C17',1467,1497,'ATH objective was not reached in the reviewed week','presenter_acknowledged_limit','explicit_in_source','Chart 13; nearer hourly highs described as terminal draw.'),
('C18',1489,1497,'Next Monday could resume toward ATH','presenter_forecast','outcome_not_evaluated','Do not convert this forward scenario into a completed result.'),
('C19',1497,1588,'Weekly context should guide intraday direction','presenter_method_summary','qualitative_only','Chart 14; no baseline comparison or out-of-sample result.'),
('C20',0,1631.401,'Sweep/BOS/OB confirmations may overlap statistically','reviewer_inference','methodological_caution','They can describe the same path; independence is not established.'),
('C21',0,1631.401,'Mechanical replication requires additional definitions','reviewer_assessment','source_scope_limit','Swing choice, zone construction, invalidation, fills and costs remain underspecified.')]
table('claims.csv',['claim_id','start_seconds','end_seconds','claim_summary','attribution','evidence_status','qualification'],claims)
(W/'advice.md').write_text('''# Interpretation as of October 5, 2026

Use this lesson as a source of hypotheses about context, confirmation, and
abstention. Its strongest teaching example is the information gained between the
first area of interest and a later confirmed entry (claim C11; chart 06). Thursday
shows that a bullish view does not require a position (C14; chart 09).

The video does not establish a profitable strategy. Preserve the unverified
quarterly claim (C06), unaudited opportunity magnitudes (C08–C09), and explicit
all-time-high shortfall (C17; chart 13). Friday illustrates revision after observed
news response, not verified prediction of a release (C15).

No execution costs, market simulation, fills, or net returns were tested. Do not
promote this source review to a validated strategy card. If pursued, first define
causal swings, zones, structure breaks, fills, invalidation and session timing;
then compare bias and confirmation filters against simpler baselines on new,
pinned market-data samples. The reviewed week is already a development example.

Evidence: [claim ledger](tables/claims.csv), [chart atlas](tables/charts.csv), and
[detailed report](report.md). Negative and unresolved evidence remains part of the
record. These conclusions apply to this one source review only.
''')
(W/'acquisition.md').write_text('''# Acquisition and reproduction

The user supplied the YouTube URL. Source review used the full automatic English
caption export and fourteen inspected player frames. The full video was not
saved. No source trading figures were recalculated.

## Source access

The web text reader returned a cache miss. YouTube oEmbed returned the video title
and Tmac channel identity. The connected Chrome browser displayed the title,
27:11 duration, and an expanded description showing October 5, 2026. Only relevant
source metadata was retained; recommendations, account details and comments were
excluded. The browser's content.exportYouTubeTranscript() exported the UTF-8
English automatic captions. The source lock pins the retained copy.

The browser opened the supplied URL, paused playback, and sought using the player
seek slider in five-second steps. After seeking, the page was scrolled to the top
and a settled paused frame was captured with:

```javascript
const media = await tab.playwright.locator('#movie_player').evaluate(el => {
  const v = el.querySelector('video');
  return {currentTime:v.currentTime,duration:v.duration,paused:v.paused,readyState:v.readyState};
});
const bytes = await tab.screenshot({clip:{x:14.4,y:61.2,width:1196.55,height:673.05}});
```

The browser capture scale produced 1329 by 748 pixel JPEG player excerpts.
Early captures used settled displayed player times; captures 06–14 additionally
record the paused media time in capture-log.json. Seeking can leave the ARIA
label temporarily stale. Frame 06 was recaptured at 923.829009 seconds using the
media check. Original chart annotations and facecam remain; there are no generated
charts, reconstructed candles, or synthetic fills. Image selection was purposive.

## Local commands

Commands run from the Abacus workspace root. The publication root of `.` was
read from config/paths.local.toml before source retention and supplied explicitly.
The authoring script is preserved as provenance/source-authoring.py. It creates
tables and metadata from the inspected source and copies the caption input into
retained research storage. Its temporary input path is historical acquisition
provenance; later verification uses the portable path in inputs.lock.json.

```sh
python3 work/17_nq_advanced_amd_video/prepare.py
python3 studies/17_nq_advanced_amd_video/run.py assemble --source work/17_nq_advanced_amd_video --bundle work/17_nq_advanced_amd_video/20261005T172713Z_video17 --publication-root .
python3 studies/17_nq_advanced_amd_video/run.py verify --bundle runs/17_nq_advanced_amd_video/20261005T172713Z_video17 --publication-root .
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py
python3 scripts/build-research-index.py --check
```

The exact sealing command is recorded in manifest.json. The report is rendered
from authored Markdown and saved image/table evidence using the snapshot of the
study-specific standard-library packager. A later re-render must go to a new
presentation revision, not overwrite this completed run. The run's code snapshot
preserves dirty/untracked study source; the Git status is context for unrelated
pre-existing workspace changes, not a claim to snapshot the entire repository.

## Review scope

All caption intervals are assigned a review note in tables/coverage.csv, from
0 through the media duration. Screenshot inspection covers the selected visual
examples, not every frame of the 27-minute video. The evidence does not include
independent listening verification of every auto-caption, the original private
messages, an account statement, tick history, or an independently reconstructed
news release. Ambiguous jargon remains unresolved.
''')
print('Prepared source lock, 14 chart records, 18 coverage intervals and 21 claims.')

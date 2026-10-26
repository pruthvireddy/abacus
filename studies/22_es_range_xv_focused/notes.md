# Decisions and inspection history

## 2026-10-12 — initialize the focused ES module

The user requested a new study module for ES Range XV, with yearly results and
the seven specified session/timeframe breakdowns for all future statistics.
Initialize study 22 without inventing an event, statistic or research outcome.
Implement the reporting helper and a read-only scope description.

Use New York time, consistent with the existing enhanced exports. Interpret
19.30, 9.30 and similar notation as 19:30, 09:30, etc. Boundaries include the
start and exclude the end. Base-bar membership uses opening time; future
event-based metrics must declare causal grouping time before execution.

Use inferred trading-session year from `session_date_proxy`, keeping overnight
windows within the existing 18:00-rollover convention. Preserve overlaps and
all-hours observations outside the named windows. Require yearly-by-window
tables as well as separate annual and all-years window sections.

The user has not selected one Range XV setting. Pin ES 4/5/6 separately from
the long-history snapshot; selecting the first analysis universe remains part
of the next metric specification. Available OHLC and absent volume were inspected
earlier in this chat. Coverage, column names and manifest inventory were reviewed;
no new statistical outcomes or feature selection were examined for this study.
Other Range XV studies already exist; future predictive claims must disclose
relevant prior inspection instead of asserting the whole history is untouched.

`study.yaml` deliberately uses JSON syntax, valid YAML 1.2, to avoid adding a
parser dependency to the locked workspace. Study 22 owns its helper/tests and
is registered in the existing verification registry. No completed run exists.

## 2026-10-12 — authorize trend-length analysis and Vercel publication

The user explicitly requested overall statistics as well as annual/session
breakdowns, the first directional trend-length analysis for all three settings,
and a final study webpage with chart tabs visible on Vercel. This authorizes the
local analysis, verified sealing, selected publication and production release.

Before viewing outcomes, freeze protocol 0.2.0: exact candle close-open sign,
doji breakers, completion-proxy population, no cross-session stitching, unknown
starts/ends censored, full final partial session excluded. Group by first-candle
start time; do not cut trends at named windows. Preserve all original rows,
including identical timestamp/OHLC rows, with flags rather than speculative
removal. Require independent source reconstruction and all-cell summary checks.

## 2026-10-12 — authorize reversal continuation and F1 recovery

The user requested continuation probabilities after a reversal and retracement
followed by a favorable continuation close, with a navigable study and website.
They confirmed immediate F1 body retracements at 25/50/75/100% and a close
strictly beyond R.close. Protocol 0.3.0 uses adjacent completed opposite signs,
n=1–20 additional candles excluding R, causal completion-time window groups,
horizon-specific unknown outcomes and distinct joint/conditional F1 rates.
Definitions were selected before the new outcomes. Preserve the first run and
its publication IDs; new numerical files/settings/protocol, evidence run and
six selected continuation/retracement reports are separate. The existing Vercel
publication authorization continues for this requested website extension.

## 2026-10-12 — preceding-leg segmentation and completed reversal run

The user added preceding-leg size tables for every reversal statistic, with a
three-candle short leg followed by bullish R and two followers as an example.
Before the new execution, freeze exact known-start buckets 1–10, 11–15, 16–20,
21+ and unknown_start, plus all. Unknown observed starts never enter an exact
size bucket. Every event belongs to one disjoint size cohort plus all.

Select run `20261012T214714Z_reversals22_36f9c1` after reconstruction of all
890,921 events and all saved table cells. The 156 actual numerical tests passed
without skips. Independent publication transfer checked every selected cell and
CSV string. Six immutable continuation/retracement sources were prepared before
sealing; byte-identical presentation revisions use prefix
`20261012T220000Z_reversalweb22`. Retain the first trend run and its publication
IDs. The current reference advances to the new requested analysis; old evidence
and frozen notes/protocols remain unchanged.

## 2026-10-12 — authorize earlier A → one B → resumption R

The user requested earlier trend length → one candle pullback → reversal back in
A direction, continuation/retracement and execution/payoff if feasible, with
all original yearly/window groups and 4/5/6 web tabs. Protocol 0.4.0 freezes
the A/B/R selection and earlier-A size cohorts before its new outcomes. A=1
is retained; unknown A starts remain separate. Prior reversal statistics were
already inspected, so this is exploratory and no historical year is claimed
as untouched out-of-sample evidence.

The bounded input inventory found no delivered tick/quote data or RXV contract
IDs/roll treatment. Therefore actual executable P&L cannot be established.
Freeze a gross OHLC proxy: F1.open reference entry, stop one nominal 0.25 price
step beyond adverse B/R extreme, 1R/2R targets, ten physical completed bars,
opening-cross precedence, explicit stop/target ambiguity bounds, observed-close
timeout and unresolved barrier exclusions. No costs, dollars or portfolio
equity are invented. Store the feasibility inventory with the new run. Separate
new source modules, ledgers, saved tables, nine pre-seal reports and publication
IDs preserve both preceding completed studies and their existing publications.

## 2026-10-12 — completed earlier-trend pullback study

Select `20261012T230640Z_pullbacks22_4f3a92`: 217,366 setups, both proxy scenarios
per setup, 269 actual focused tests without skips, independent full reconstruction
and all-table verification. Selected transfer checked 519,804 numeric cells and
2,673,000 exact CSV cells. Nine byte-identical exports use prefix
`20261012T231219Z_pullbackweb22`; prior runs/publications stay unchanged. Overall
continuation remains about 80% at n=1 and 52% at n=2, while both fixed gross
OHLC payoff scenarios have negative mean R before costs. Read the sealed findings
and exact saved rows; no executable profitability conclusion is implied.
The default workspace gate remains blocked on two pre-existing missing Bhishma
continuous-roll inputs, with subsequent default checks unexecuted. Study checks
and required publication checks are separately selected and recorded.

## 2026-10-13 UTC — explanatory candle panels

The user requested minimal candle-pattern visuals for every analysis and the
measured part of each numerical section. Presentation-only prefix
`20261013T023659Z_patterns22` adds 18 immutable revisions across the six views
and 4/5/6 charts, without changing any numerical run or statistical definition.
All 216 numerical sections reference an authored diagram and focus caption.
Independent transfer checks preserved 876,330 numeric cells, 124,947 saved rows,
54 CSV files and all earlier public artifact bytes. A separate semantic review
checked mirrored geometry, R-body depths, count anchors, physical payoff bars,
censoring and unresolved dual touches. These are illustrative schematics, not
new historical candle samples or performance results. Earlier reports remain
reachable as related presentations. Ten presentation-export tests passed; the
market analysis was not rerun. Narada owns generic SVG rendering and validation.

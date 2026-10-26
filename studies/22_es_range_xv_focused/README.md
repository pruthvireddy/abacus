# Focused ES Range XV study

Study `22_es_range_xv_focused` · Trend length and reversal analyses completed and sealed.

The [public focused study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
has six analysis views, each with 4/5/6 RXV tabs. Compact candle schematics explain
the setup and measured part of every numerical section. Reversal and pullback
tables have year, session and leg-length filters; exact counts and unrounded
rates are available as CSVs.

The first analysis measures the number of consecutive completed bullish or
bearish candles in each directional trend, separately for ES 4-, 5- and 6-tick
charts. Exact lengths require observed starts and ends; boundary-censored runs
are retained separately. A doji ends a run. Trends keep their full length across
named windows and are grouped by the first candle's opening time.

Read the [plan](plan.md), [settings](study.yaml), [input lock](inputs.lock.json)
and [decisions](notes.md) before extending the [entry point](run.py) or
[timeframe module](src/timeframes.py).

For reversal work, read the separate [protocol 0.3.0](reversal-plan.md),
[reversal settings](reversal.yaml), [entry point](reversal_run.py) and
[independent verifier](reversal_audit.py). These preserve the first analysis's
protocol 0.2.0 and completed evidence. New numerical work always needs a new run.

## Required breakdowns

Every statistic must have an overall result, a yearly breakdown, a breakdown
by every window below, and a year-by-window breakdown. Years use
`session_date_proxy`, the existing inferred trading date with an 18:00 New York
rollover. Show 2019 and 2026 as partial coverage years.

All times are **America/New_York** local wall time, with daylight saving time.
Intervals include their start and exclude their end.

| Group | Window | Start | End |
|---|---|---|---|
| Session | Asia | 20:00 | 02:00 next day |
| Session | London | 02:00 | 09:00 |
| Session | NY | 09:30 | 16:00 |
| Subwindow | Asia Open | 19:30 | 21:30 |
| Subwindow | NY Open | 09:30 | 10:30 |
| Subwindow | NY AM | 10:30 | 12:30 |
| Subwindow | NY PM | 12:30 | 16:00 |

Windows are independent filters. Asia Open overlaps Asia and starts before it;
the NY subwindows also belong to NY. Their counts cannot all be summed.
Observations outside named windows remain in the all-hours and yearly totals.
Base bar descriptions use `bar_start_timestamp`. Each later event statistic must
declare its grouping timestamp and causal `available_at` before execution.

## Inputs and current limits

The longer ES snapshot covers inferred session dates 2019-11-01 to 2026-09-24,
with 1,783 recorded dates per setting. It contains OHLC and timestamp proxies,
without volume. The final session is partial. Review the
[data guide](../../data/range_xv/README.md) and
[long-history audit](../../docs/range-xv-long-history-20260924.md).
New York clock conversion is inferred; exact bar completion and contract/roll
treatment are unverified. Do not convert enhanced timestamps again.

## Inspect and verify from the workspace root

`study.yaml` uses JSON syntax, a YAML 1.2 subset, so the scaffold needs only the
standard library and the existing locked workspace environment.

```sh
./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/run.py describe
./scripts/check-workspace --check study-22
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 scripts/build-research-index.py --check
```

`describe` reads the local settings and input lock without market-data execution.
The tests use synthetic examples to check grouping, directional runs, censoring,
quantiles, saved-cell transfers and lifecycle guards. The independent
[audit](audit.py) reconstructs every run from input OHLC without importing the
engine and recomputes all saved statistics and coverage cells.

Authorized numerical stages use a new unique run ID:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/run.py execute --out work/22_es_range_xv_focused/NEW_UNIQUE_RUN
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/audit.py --stage work/22_es_range_xv_focused/NEW_UNIQUE_RUN --ledger-dir work/22_es_range_xv_focused/NEW_UNIQUE_RUN/evidence --publication-root . --output work/22_es_range_xv_focused/NEW_UNIQUE_RUN/verification.json
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/run.py render --out work/22_es_range_xv_focused/NEW_UNIQUE_RUN
```

Before `seal --out <stage>`, retain the actual ordinary numerical-test result and
artifact-bound preseal checks. The sealer refuses changed sources, results or
verification receipts. New stages belong under `work/22_es_range_xv_focused/`;
completed evidence follows the [run lifecycle](../../runs/README.md), with large
ordered trend ledgers retained separately in ignored research storage. Public
report values retain six decimals before display formatting; selected CSVs
preserve the full original saved strings.

## Completed first analysis

Reference run [20261012T201757Z_trends22_eaa65b](../../runs/22_es_range_xv_focused/20261012T201757Z_trends22_eaa65b/manifest.json)
is explicitly selected for the first requested statistic after independent
source reconstruction and all-cell checks. Read the
[report](../../runs/22_es_range_xv_focused/20261012T201757Z_trends22_eaa65b/report.md),
[saved summaries](../../runs/22_es_range_xv_focused/20261012T201757Z_trends22_eaa65b/tables/trend_summary.csv),
[independent audit](../../runs/22_es_range_xv_focused/20261012T201757Z_trends22_eaa65b/verification.json)
and [retained-ledger locators](../../runs/22_es_range_xv_focused/20261012T201757Z_trends22_eaa65b/events.manifest.json).

| Chart | Direction | Exact trends | Mean candles | Median | P90 | Maximum |
|---|---|---:|---:|---:|---:|---:|
| 4 RXV | Bullish | 202,765 | 3.15 | 2 | 6 | 41 |
| 4 RXV | Bearish | 202,815 | 3.13 | 2 | 6 | 36 |
| 5 RXV | Bullish | 138,903 | 3.16 | 2 | 6 | 37 |
| 5 RXV | Bearish | 138,996 | 3.14 | 2 | 6 | 29 |
| 6 RXV | Bullish | 101,023 | 3.17 | 2 | 6 | 50 |
| 6 RXV | Bearish | 101,073 | 3.15 | 2 | 6 | 33 |

All 896,267 observed trends were independently reproduced, including 885,575
exact trends and 10,692 censored trends. The 73 focused tests passed without
skips. These summaries describe fully observed candle-colour trends; they do
not establish future continuation probability or trading profitability.

The [selected public study](https://abacus-narada.vercel.app/studies/es-range-xv-trend-length/)
has separate chart tabs. [export.py](export.py) copies verified pre-seal sources
into unique presentation revisions without recalculating evidence. The frozen
run's settings, protocol, inputs and source snapshots remain authoritative.

## Completed reversal analysis

Run [20261012T214714Z_reversals22_36f9c1](../../runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/manifest.json)
contains 890,921 observed reversals, independently reconstructed from all
2,815,095 input rows. Every saved summary, continuation, retracement and coverage
cell matched. All 156 focused tests passed without skips. A separate transfer
audit checked all 344,652 displayed numeric cells and 1,739,880 selected CSV cells.

R is a completed candle directly after an opposite completed candle. n means
additional uninterrupted same-colour candles **after R**, excluding R. Every
horizon retains its own success/failure denominator and unknown outcomes.
F1 body retracements use 25/50/75/100%; a favorable close must be strictly beyond
R.close. Joint rates use every known F1, while conditional rates use touched F1.

All metrics include exact preceding lengths 1–10, 11–15, 16–20, 21+ and a separate
unknown-start cohort, as well as the overlapping all cohort. A known 3-candle
bearish leg followed by bullish R and two bullish followers is a success at n=2
in the bullish reversal / prior length 3 group. Its overall known-outcome rates
are 47.72%, 47.85% and 47.86% for 4/5/6 RXV. This is descriptive history.

Read the [report](../../runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/report.md),
[metric index](../../runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/metrics.json),
[retracement table](../../runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/tables/reversal_retracement.csv)
and [audit receipt](../../runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/verification.json).
The saved continuation table is retained at
`runs/22_es_range_xv_focused/20261012T214714Z_reversals22_36f9c1/tables/reversal_continuation.csv`
from the workspace root. This file is excluded from Git and requires exact-byte
restoration from a separately retained copy; its size and hash are recorded in
the [GitHub bulk artifact inventory](../../docs/github-bulk-artifacts.json).
Events are grouped by R's completion proxy, rather than the first analysis's
opening-time descriptive anchor. Follow-up crosses named-window endpoints but
never crosses daily sessions or completion barriers. Unknown outcomes are not
failures; unknown preceding starts are not assigned an invented exact length.

Reproduction uses a fresh unique stage with the same locked environment:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/reversal_run.py execute --out work/22_es_range_xv_focused/NEW_UNIQUE_REVERSAL_RUN --publication-root .
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/reversal_audit.py --stage work/22_es_range_xv_focused/NEW_UNIQUE_REVERSAL_RUN --output work/22_es_range_xv_focused/NEW_UNIQUE_REVERSAL_RUN/verification.json
UV_CACHE_DIR=/private/tmp/abacus-study22-uv-cache ./scripts/uv run --locked --no-sync python studies/22_es_range_xv_focused/reversal_run.py render --out work/22_es_range_xv_focused/NEW_UNIQUE_REVERSAL_RUN
```

Before sealing, record actual numerical tests and artifact-bound preseal checks.
[reversal_export.py](reversal_export.py) copies the six verified pre-seal sources
into separate immutable presentation revisions without recalculating statistics.

## Earlier trend and one-candle pullback

[Protocol 0.4.0](pullback-plan.md) and [settings](pullback.yaml) define earlier
directional A → exactly one opposite B → resumption R. The length cohort measures
A before B. Continuation and F1 retracement retain their original definitions,
with every overall/year/window combination and all 4/5/6 chart settings.

The optional payoff view is a gross OHLC proxy: F1.open reference, a structural
B/R stop with nominal 0.25 buffer, separate 1R/2R targets and ten physical bars.
Opening gaps, ambiguous intrabar order and unresolved barriers remain explicit.
Actual fills, costs, contract-adjusted dollar P&L and portfolio returns cannot be
established from these inputs. Read the protocol before interpreting its bounds.

[pullback_run.py](pullback_run.py) executes/renders/seals only new stages;
[pullback_audit.py](pullback_audit.py) independently reconstructs all setup and
payoff ledgers and every saved cell. [pullback_export.py](pullback_export.py) copies
nine selected pre-seal sources into unique presentation revisions. Frozen sources
and the sealed run remain authoritative; previous studies are preserved.

Selected run [20261012T230640Z_pullbacks22_4f3a92](../../runs/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/manifest.json)
contains 217,366 setups and 434,732 proxy scenarios. All 269 focused tests passed
without skips; independent reconstruction matched every event/table cell.
Independent web transfer checked 519,804 numeric cells and 2,673,000 original
CSV cells across nine reports. Read the [findings](../../runs/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/findings.md),
[saved payoff table](../../runs/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/tables/pullback_payoff.csv),
[audit](../../runs/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/verification.json)
and [feasibility inventory](../../runs/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/execution-feasibility.json).

Overall one-candle continuation is about 80%, but both fixed payoff scenarios
have negative gross mean R even under their favorable order bounds. This does
not establish executable net performance. All years remain exploratory.

## Candle-pattern presentation revisions

[pattern_export.py](pattern_export.py) prepares and exports separately verified
presentation revisions of all 18 selected reports. It adds illustrative candle
geometry and explicit section focus while preserving every existing value,
description, source binding and CSV byte. Frozen numerical runs remain unchanged.
New IDs end in `-patterns-r1`; the authored public catalog retains the earlier
reports as related presentations.

Revision prefix `20261013T023659Z_patterns22` contains the 18 selected copies under
their original source runs. Read the [4 RXV retracement revision](../../reports/exports/22_es_range_xv_focused/20261012T230640Z_pullbacks22_4f3a92/20261013T023659Z_patterns22_pullback-retracement_4t/manifest.json).
Independent review covered all 216 numerical-section diagram references,
876,330 unchanged numeric cells, 124,947 saved rows and 54 unchanged CSVs.
Diagram correctness was checked separately from numerical evidence validity.
Only the 10 focused presentation-export tests were needed; no market analysis
or historical numerical suite was rerun for this presentation change.

# EMA6 crossings of Globex VWAP

Descriptive ES/NQ/GC crossing frequency study. Read the [plan](plan.md),
[current protocol](protocol-1.1.0.md), [settings](study.yaml),
[input lock](inputs.lock.json) and [decisions](notes.md).

Current analysis uses a **6-period EMA on 3-minute closing prices**. Counts cover full
Globex, a common 09:30–16:00 New York window, GC bar opens 08:21–13:27, and an opening-bar
sensitivity. Volatility is both prior available ATR14% ranked over 252 earlier
observations and realized session range divided by pre-session ATR14. The latter
is known after the day. Existing conservative VWAP eligibility limits coverage.
Three-minute bars/VWAP are study-local derivatives of pinned minute data through
existing Bhishma helpers; published releases remain unchanged. The earlier
[protocol](protocol-1.0.0.md) and its 5m/2m evidence remain historical records.

## Current three-minute findings

The reviewed reference is [20261023T210215Z_ema6_3m_v1](../../runs/28_globex_ema_crossings/20261023T210215Z_ema6_3m_v1/report.html),
with a [Markdown report](../../runs/28_globex_ema_crossings/20261023T210215Z_ema6_3m_v1/report.md).
It uses EMA length **6**, source **close**, timeframe **3 minutes**, with a matching
three-minute HLC3/volume Globex VWAP anchored at 18:00 New York.
Over June 28, 2021–September 18, 2026, mean crossings per full session were:

| Product | Eligible sessions | All days | Quiet days | Active days |
| --- | ---: | ---: | ---: | ---: |
| ES | 1,037 | 10.98 | 12.86 | 8.80 |
| NQ | 1,177 | 10.72 | 13.03 | 8.73 |
| GC | 418 | 9.39 | 12.35 | 7.67 |

Values come from the [saved summary](../../runs/28_globex_ema_crossings/20261023T210215Z_ema6_3m_v1/tables/summary.csv)
with `timeframe=3m`, `window=globex`, `cohort=common_calendar`. Quiet means eventual
session range <0.75 prior ATR; active means ≥1.25 ATR. These labels are known after
the day. Prior available ATR14% regimes remain separately reported.
The [annual](../../runs/28_globex_ema_crossings/20261023T210215Z_ema6_3m_v1/tables/yearly.csv) and
[calendar-month](../../runs/28_globex_ema_crossings/20261023T210215Z_ema6_3m_v1/tables/monthly.csv) tables include
volatility segments and sample sizes. The report includes common US cash hours,
GC-day bar-open membership, opening-bar sensitivity and 357 matched dates.

All 25 synthetic tests passed. Independent verification reconciled 1,397,940
source-derived bars, 32,006 crossings, 21,826 daily-panel rows, all saved summary
cells and nine source-EMA sessions. Coverage, full-session ranges, ATR values and
volatility labels match the earlier run. GC coverage remains especially selected
and sparse. The current workspace default gate retained the same two historical
data-integration prerequisite errors; the explicit remaining checks passed.
Both the new 107-artifact bundle and original 100-artifact bundle passed their
separate integrity checks. The earlier run below remains unchanged.

## Earlier 5m/2m findings (preserved)

Run `20261023T202400Z_ema6_v1` is sealed with an independently verified
[offline report](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/report.html)
and [Markdown report](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/report.md).
For 5-minute bars over June 28, 2021–September 18, 2026, full-Globex crossings
averaged:

| Product | Eligible sessions | All days | Quiet days | Active days |
| --- | ---: | ---: | ---: | ---: |
| ES | 1,037 | 8.42 | 9.79 | 6.75 |
| NQ | 1,177 | 8.31 | 10.10 | 6.96 |
| GC | 418 | 7.33 | 9.54 | 5.83 |

Values are mean crossings per session from the saved
[summary table](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/tables/summary.csv)
with `timeframe=5m`, `window=globex`, `cohort=common_calendar`.
Quiet means realized session range <0.75 prior ATR; active means ≥1.25 ATR.
This classification is known after the day. The same ordering holds on the
357 shared eligible dates; prior available ATR bins show modest, inconsistent
separation. Coverage is selected and uneven, particularly for GC.

The saved [annual](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/tables/yearly.csv)
and [calendar-month](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/tables/monthly.csv)
tables include volatility segments and sample sizes. Years 2021 and 2026 are
partial; small monthly cells do not establish stable seasonality. The report
also includes 2-minute, cash-window and opening-bar sensitivity comparisons.

## Run and verify

From the workspace root, use the existing locked environment without sync for
numerical calculations, tests, verification and sealing. Supply an existing
Python interpreter with matplotlib through `--plot-python`; the locked numerical
environment does not include matplotlib.

```sh
UV_CACHE_DIR=/private/tmp/abacus-study28-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/28_globex_ema_crossings/tests
UV_CACHE_DIR=/private/tmp/abacus-study28-uv-cache ./scripts/uv run --locked --no-sync python studies/28_globex_ema_crossings/run.py --run-id <new-run-id> --plot-python <existing-python-with-matplotlib>
./scripts/check-workspace --check study-28
UV_CACHE_DIR=/private/tmp/abacus-study28-uv-cache ./scripts/uv run --locked --no-sync python studies/28_globex_ema_crossings/verify_saved_v3.py --stage work/28_globex_ema_crossings/<new-run-id>
UV_CACHE_DIR=/private/tmp/abacus-study28-uv-cache ./scripts/uv run --locked --no-sync python studies/28_globex_ema_crossings/seal.py --stage work/28_globex_ema_crossings/<new-run-id>
```

The runner freezes exact producer/input/environment bytes before calculations,
verifies selected input partitions, and leaves staged evidence in `work/`.
The separate existing cached plot environment runs [render_figures.py](render_figures.py)
on saved tables only. Its executable and Python, matplotlib and NumPy versions
are recorded in the stage's `figure-environment.json`; the numerical calculation
continues to use the locked environment without synchronization.

Use the [version 3 verifier](verify_saved_v3.py) for independent saved-evidence
checks, including source reconstruction of three-minute OHLCV/VWAP and unchanged
ATR/eligibility against the earlier run. The earlier verifiers remain retained. Completed runs require its passed verification
receipt before [sealing](seal.py) to a fresh destination; no existing run is
modified. This study does not test trade returns or publish a hosted website.

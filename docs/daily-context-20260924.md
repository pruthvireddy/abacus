# TradingView daily context snapshot — 2026-09-24

Bhishma retains the nine downloaded chart CSVs exactly as received under
`data/raw/tradingview/chart_exports/1d/20260924-8722875f919f/`. The batch
manifest records each original filename, byte count, and SHA-256. The release
manifest is [tradingview_daily_context__1.0.0.json](../catalog/datasets/tradingview_daily_context__1.0.0.json)
(`b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f`).
The [schema](../catalog/schemas/tradingview_daily_context__1.0.0.json),
[indicator definitions](../catalog/indicators/tradingview_daily_context__1.0.0.json),
and [user-supplied Pine script](../catalog/indicators/tradingview_daily_context__1.0.0.pine)
describe the delivery. The [request snapshot](../requests/fulfilled/tradingview_daily_context__1.0.0.yaml)
records the intended use. See the [quality report](../reports/quality/tradingview_daily_context__1.0.0.md)
for coverage and gaps.

The analysis-ready copy contains 87,554 **confirmed** rows, one Parquet file per
asset under `data/features/bars/1d/feature_set=tradingview_daily_context/version=1.0.0/asset=<asset>/`.
The nine files total about 27 MB, so year partitions add unnecessary file
overhead. All 47 exported columns are retained, with empty cells as nulls.
Bhishma adds `asset`, `source_symbol`, `trading_day`, and `available_at`.
The six unfinished 2026-09-24 rows remain only in the immutable raw CSV copies.
Do not overwrite this release; a later export is a new source batch and version.

## Dates and use with lower timeframe data

`trading_day` is the exported `trading_day_utc_unix_s` date. Futures and spot
daily bars can open on the **previous UTC date**; joining on raw `time`'s date
would shift them. `available_at` is the exported `bar_close_unix_s` converted to
a UTC timestamp. It is the earliest time at which the complete bar and all its
indicators may be used in a causal lower-timeframe study. The CSVs are a later
chart snapshot, so historical provider revisions and chart settings have not
been point-in-time certified.

```python
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from abacus_bhishma.daily_context import align_daily_context_asof

root = Path("/Users/ppanati/Documents/projects/abacus")
ny = ZoneInfo("America/New_York")
intraday_times = [
    datetime(2026, 9, 23, 15, 0, tzinfo=ny),
    datetime(2026, 9, 23, 17, 0, tzinfo=ny),
]
vix = align_daily_context_asof(
    root, "VIX", intraday_times, version="1.0.0",
    columns=("trading_day", "available_at", "close", "atr14"),
)
es = align_daily_context_asof(
    root, "ES", intraday_times, version="1.0.0",
    columns=("trading_day", "available_at", "atr14", "atr14_pct"),
)
```

This returns the prior completed VIX and ES bars at 15:00 New York time, and
the September 23 completed bars at 17:00. The helper reads each asset once for
the supplied timestamp batch and returns `None` before coverage or if the last
available bar is more than seven calendar days old. `max_age_days=None` disables
that age limit explicitly. Use timezone-aware lower-timeframe timestamps.

For retrospective descriptions of a whole day, `load_daily_context(...,
start_date="2026-09-23", end_date="2026-09-24")` selects the finished day's
row. Such a same-day final value is only known after `available_at`; it must
not be assigned to earlier intraday observations in causal analysis. The
`warmup1000_complete` field is retained for studies requiring that history.

Indicators are copied from the export, not recomputed from Abacus's Databento
data. The provided Pine script defines ATR(14), EMA(20/50), SMA(200),
RSI(14), DMI/ADX(14), Bollinger bands, prior-bar Donchian windows,
annualized realized volatility, ROC, volume comparisons, MACD, and ATR
normalizations. The source chart controls sessions, settlement, underlying
prices, and continuous-futures rolls. Do not treat the chart's ES/NQ/GC
continuous prices as identical to Bhishma's own continuous contract series.
The Parquet price and indicator fields are float64 parsed from the source CSV;
they are context values, not Abacus execution-price inputs.

Bulk files under `data/` are Git-ignored. Back up the raw batch and feature
directory together with this tracked catalog release.

After restoring data on another machine, verify every raw and feature file:

```sh
./scripts/uv run --locked python -m abacus_bhishma.daily_context \
  --root . --verify \
  --manifest-sha256 b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f
```

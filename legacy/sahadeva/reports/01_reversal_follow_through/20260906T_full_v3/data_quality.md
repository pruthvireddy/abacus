# Data quality findings

## Inventory

- ES range 4 `ESU6_rangexv4_0614_0904.csv`: 52,591 rows; 52,591 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 4,608 rows participate in repeated timestamps; 6 dojis.
- ES range 5 `ESU6_rangexv5_0614_0904.csv`: 36,188 rows; 36,188 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 2,702 rows participate in repeated timestamps; 8 dojis.
- ES range 6 `ESU6_rangexv6_0614_0904.csv`: 26,248 rows; 26,248 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 1,713 rows participate in repeated timestamps; 5 dojis.
- GC range 10 `GCZ6_rangexv10_0614_0904.csv`: 67,164 rows; 67,164 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 7,330 rows participate in repeated timestamps; 2 dojis.
- NQ range 10 `NQU6_rangexv10_0614_0904.csv`: 417,815 rows; 417,815 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 126,122 rows participate in repeated timestamps; 5 dojis.
- NQ range 20 `NQU6_rangexv20_0614_0904.csv`: 125,793 rows; 125,793 day-month timestamps parsed; 0 OHLC failures; 0 off-tick rows; 0 regressions; 15,893 rows participate in repeated timestamps; 3 dojis.

- GC range 20 is missing and remains unestimated.
- GC range 6 is present but inventory-only. It was not renamed, substituted, or used in performance calculations.
- Every source SHA-256 and byte size is recorded in `tables/data_audit.csv` and `run_manifest.json`. `data/` was read only.

## Schema and timestamps

Every analyzed file has exactly five semicolon-separated fields per parsed row and no header row. The first field parses completely with `%Y-%d-%m %H:%M:%S`; the ordinary year-month-day alternative parses only the ambiguous subset and is rejected. Timestamps are nondecreasing, but repeats are common and sometimes adjacent. Original row number resolves tied timestamps.

Timezone and timestamp meaning are absent. Consequently, parsed dates are **provisional export dates**, not verified trading sessions; timestamp differences are labeled proxies; exact extreme times are unavailable; and a common clock-window comparison is unsupported. A file-sequence boundary sensitivity is reported separately.

## OHLC and tick geometry

All analyzed rows satisfy `high >= max(open, close, low)` and `low <= min(open, close, high)`. Prices align to CME tick sizes. Distributional geometry is in `tables/geometry.csv`. These are observed properties, not a reconstruction of ATAS's proprietary chart-building algorithm.

## Coverage and exclusions

The analyzed files cover the same 72 parsed export dates from 2026-06-14 through 2026-09-04, with differing bar counts and final intraday timestamps. The final row of each analyzed export is excluded because bar completion cannot be established. Threshold and horizon exclusions are reported explicitly in their result tables. Dojis break event adjacency and runs.

## Missing metadata that could change interpretation

Exact ATAS version and settings, Range XV versus the user's earlier Range XC label, parameter units, export timezone, bar-open versus bar-close timestamps, completed-bar status, data feed, contract/roll history, continuous-contract adjustments, and session calendar remain unresolved. None was guessed.

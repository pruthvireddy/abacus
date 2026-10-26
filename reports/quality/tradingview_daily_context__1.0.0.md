# Daily context 1.0.0 quality record

Source: nine TradingView chart CSV downloads on 2026-09-24. Each has the same
47-column export layout. The immutable source batch and all nine Parquet outputs
were SHA-256 verified against the [release manifest](../../catalog/datasets/tradingview_daily_context__1.0.0.json).
The release contains 87,554 confirmed bars; six unconfirmed final rows were
excluded and kept in raw storage. Rows have strictly increasing bar-open,
bar-close, and availability timestamps with no duplicate trading days.
Four direct formula identities (`atr14_pct`, `bb20_bandwidth_pct`,
`macd_hist_atr14`, and `dist_ema20_atr`) were checked across every non-null
published row with zero mismatches. This check does not recompute all
indicators or establish the source chart's historical settings.

| Asset | First trading day | Last completed day | Confirmed rows | Unconfirmed excluded |
|---|---:|---:|---:|---:|
| XAUUSD | 1833-01-07 | 2026-09-23 | 14,856 | 1 |
| SI | 1970-01-05 | 2026-09-23 | 14,247 | 1 |
| CL | 1983-03-30 | 2026-09-23 | 10,931 | 1 |
| GC | 1975-01-02 | 2026-09-23 | 13,011 | 1 |
| ES | 1997-09-09 | 2026-09-23 | 7,344 | 1 |
| NQ | 1999-06-30 | 2026-09-23 | 6,887 | 1 |
| GVZ | 2008-08-01 | 2026-09-23 | 4,562 | 0 |
| VIX | 1990-01-03 | 2026-09-23 | 9,268 | 0 |
| VXN | 2001-01-24 | 2026-09-23 | 6,448 | 0 |

## Coverage and nulls

- XAUUSD's 1833–1920 records are sparse annual observations, 1921–1969 are
  roughly monthly, and daily records begin in 1970. Its daily-era history has
  **23 gaps longer than seven calendar days**, concentrated in September 1997
  through October 1998; the largest spans 28 days (1997-11-18 to 1997-12-16).
- VXN has a 12-calendar-day gap from 2017-02-10 to 2017-02-22. The other
  assets have no gap over seven calendar days in their daily histories. This
  threshold is a coverage screen, not a trading-calendar completeness test.
- GVZ, VIX, and VXN have no source volume values: `volume_raw`,
  `volume_prior20_mean`, `rvol20_prior`, and `Volume` are null throughout.
  Many XAUUSD and early futures relative-volume values are also null. No
  volume was invented or forward-filled.
- All nine files have the expected initial indicator warmups: `atr14` is null
  for the first 13 rows and `sma200` for the first 199. The source
  `warmup1000_complete` flag remains available for stricter sample selection.

The source chart's continuous-futures rolls, settlement and session settings,
historical revisions, and spot/volume semantics were not independently audited.
The user's [Pine script](../../catalog/indicators/tradingview_daily_context__1.0.0.pine)
documents formulas, while the published feature values remain parsed
numeric readings of the exported CSV columns. See the
[usage guide](../../docs/daily-context-20260924.md) for timing-safe joins.

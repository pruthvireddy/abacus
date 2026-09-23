# tv_indicators__dridr_ohlcv_5m__v1 quality report

## Result

**PASS** — the requested immutable five-minute OHLCV delivery was built and independently replayed from every pinned Phase 2 source partition.

No DR/IDR features, labels, outcomes, statistics, or Pine payloads are present.

## Coverage

| Product | 5m rows | Source 1m rows | Session dates | First 5m open UTC | Last 5m open UTC | Last source minute UTC | Partial | Roll |
|---|---:|---:|---:|---|---|---|---:|---:|
| ES | 1,145,369 | 5,694,142 | 4,195 | 2010-06-06T22:00:00.000000000Z | 2026-09-18T20:55:00.000000000Z | 2026-09-18T20:59:00.000000000Z | 25,198 | 66 |
| GC | 1,149,486 | 5,651,836 | 4,191 | 2010-06-06T22:00:00.000000000Z | 2026-09-18T20:55:00.000000000Z | 2026-09-18T20:59:00.000000000Z | 56,351 | 81 |
| NQ | 1,143,458 | 5,520,074 | 4,195 | 2010-06-06T22:00:00.000000000Z | 2026-09-18T20:55:00.000000000Z | 2026-09-18T20:59:00.000000000Z | 112,944 | 66 |

The request boundaries are midnight America/New_York instants. Coverage was not truncated to common overlap; the table reports each product independently.

## Construction contract

Databento documents `ts_event` as the inclusive start of an OHLCV interval and emits no record when no trade occurs: https://databento.com/docs/schemas-and-data-formats/ohlcv

Five-minute buckets are fixed New York-clock-aligned `:00/:05/.../:55` opens with `[start, end)` semantics. Because New York UTC offsets are integral hours, flooring the UTC nanosecond bar-open to five minutes is exactly the same alignment; timezone-aware spot checks cover both 2024 DST transition weeks.

OHLCV uses first/max/min/last/sum. Empty buckets are absent. Nonempty buckets are complete only when all five distinct opens at offsets 0–4 are present; other nonempty buckets are retained and flagged. No prices, closes, or zero-volume rows are synthesized.

## Schema

| Column | Arrow type | Nullable | Units / meaning |
|---|---|---:|---|
| `ts_event` | `timestamp[ns, tz=UTC]` | false | UTC inclusive five-minute bar open |
| `session_date` | `date32[day]` | false | exchange session label inherited from Phase 2 |
| `product` | `string` | false |  |
| `open` | `int64` | false | price; int64 fixed-point scale 1e-9 |
| `high` | `int64` | false | price; int64 fixed-point scale 1e-9 |
| `low` | `int64` | false | price; int64 fixed-point scale 1e-9 |
| `close` | `int64` | false | price; int64 fixed-point scale 1e-9 |
| `volume` | `uint64` | false | contracts; exact sum of published source-minute volume |
| `continuous_symbol` | `string` | false |  |
| `raw_symbol` | `string` | true |  |
| `instrument_id` | `uint32` | true |  |
| `roll_id` | `int16` | true |  |
| `contains_roll` | `bool` | false |  |
| `price_adjustment` | `int64` | true | price; int64 fixed-point scale 1e-9; null when mixed |
| `first_raw_symbol` | `string` | false |  |
| `last_raw_symbol` | `string` | false |  |
| `source_bar_count` | `uint8` | false | unique published one-minute source bars |
| `is_partial_bar` | `bool` | false |  |
| `min_tick` | `double` | false | price units |
| `is_mixed_contract_bar` | `bool` | false |  |
| `is_mixed_adjustment_bar` | `bool` | false |  |

Scalar `raw_symbol`, `instrument_id`, `roll_id`, and `price_adjustment` are null only when the respective source value is not constant in the bucket. `first_raw_symbol` and `last_raw_symbol` always preserve time order. The adjustment regime identity is the exact fixed-point `price_adjustment` together with `prior_session_close_additive_v1`; `is_mixed_adjustment_bar` means more than one adjustment value occurred.

## Product/year reconciliation

| Product | Year | Source rows | 5m rows | Complete | Partial | Missing-minute events* | Unpublished minutes* | Mixed contract | Mixed adjustment | Roll | Break-window bars |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ES | 2010 | 202,121 | 40,977 | 38,813 | 2,164 | 2,452 | 4,389 | 0 | 0 | 3 | 692 |
| ES | 2011 | 351,419 | 70,803 | 68,752 | 2,051 | 2,338 | 5,413 | 0 | 0 | 4 | 1,207 |
| ES | 2012 | 348,273 | 70,364 | 67,596 | 2,768 | 3,102 | 6,504 | 0 | 0 | 4 | 1,138 |
| ES | 2013 | 341,308 | 69,127 | 65,715 | 3,412 | 3,951 | 8,046 | 0 | 0 | 4 | 748 |
| ES | 2014 | 335,357 | 68,328 | 63,635 | 4,693 | 5,402 | 9,901 | 0 | 0 | 4 | 738 |
| ES | 2015 | 350,170 | 70,785 | 67,878 | 2,907 | 3,384 | 7,443 | 0 | 0 | 4 | 551 |
| ES | 2016 | 349,041 | 70,127 | 68,806 | 1,321 | 1,637 | 5,338 | 0 | 0 | 4 | 4 |
| ES | 2017 | 344,787 | 69,813 | 66,350 | 3,463 | 4,001 | 7,988 | 0 | 0 | 4 | 5 |
| ES | 2018 | 348,998 | 70,072 | 69,180 | 892 | 1,049 | 4,509 | 0 | 0 | 4 | 60 |
| ES | 2019 | 349,531 | 70,005 | 69,556 | 449 | 713 | 4,394 | 0 | 0 | 4 | 0 |
| ES | 2020 | 350,353 | 70,270 | 69,851 | 419 | 763 | 5,297 | 0 | 0 | 4 | 4 |
| ES | 2021 | 353,364 | 70,695 | 70,594 | 101 | 225 | 1,926 | 0 | 0 | 4 | 0 |
| ES | 2022 | 354,120 | 70,827 | 70,812 | 15 | 15 | 15 | 0 | 0 | 4 | 0 |
| ES | 2023 | 353,174 | 70,690 | 70,437 | 253 | 263 | 272 | 0 | 0 | 4 | 1 |
| ES | 2024 | 354,819 | 71,013 | 70,781 | 232 | 238 | 246 | 0 | 0 | 4 | 0 |
| ES | 2025 | 352,544 | 70,518 | 70,472 | 46 | 47 | 691 | 0 | 0 | 4 | 0 |
| ES | 2026 | 254,763 | 50,955 | 50,943 | 12 | 12 | 12 | 0 | 0 | 3 | 0 |
| GC | 2010 | 197,144 | 41,235 | 35,342 | 5,893 | 6,684 | 9,484 | 0 | 0 | 2 | 421 |
| GC | 2011 | 349,750 | 71,547 | 66,029 | 5,518 | 6,121 | 8,451 | 0 | 0 | 5 | 751 |
| GC | 2012 | 344,045 | 70,761 | 64,786 | 5,975 | 6,709 | 11,435 | 0 | 0 | 5 | 736 |
| GC | 2013 | 341,144 | 69,930 | 64,734 | 5,196 | 5,891 | 9,948 | 0 | 0 | 5 | 746 |
| GC | 2014 | 334,713 | 69,208 | 62,118 | 7,090 | 7,965 | 12,936 | 0 | 0 | 5 | 728 |
| GC | 2015 | 343,266 | 71,030 | 63,633 | 7,397 | 8,381 | 13,475 | 0 | 0 | 5 | 534 |
| GC | 2016 | 348,164 | 70,665 | 67,560 | 3,105 | 3,477 | 6,148 | 0 | 0 | 5 | 1 |
| GC | 2017 | 347,021 | 70,221 | 68,178 | 2,043 | 2,303 | 5,993 | 0 | 0 | 5 | 1 |
| GC | 2018 | 347,490 | 70,242 | 68,390 | 1,852 | 2,057 | 6,696 | 0 | 0 | 5 | 24 |
| GC | 2019 | 348,353 | 70,359 | 68,648 | 1,711 | 1,922 | 5,818 | 0 | 0 | 5 | 0 |
| GC | 2020 | 350,272 | 70,491 | 69,495 | 996 | 1,120 | 4,240 | 0 | 0 | 5 | 0 |
| GC | 2021 | 348,646 | 70,402 | 68,715 | 1,687 | 1,911 | 5,717 | 0 | 0 | 5 | 0 |
| GC | 2022 | 350,005 | 70,691 | 68,926 | 1,765 | 2,024 | 4,731 | 0 | 0 | 5 | 0 |
| GC | 2023 | 347,127 | 70,276 | 68,001 | 2,275 | 2,576 | 6,199 | 0 | 0 | 5 | 0 |
| GC | 2024 | 351,770 | 70,977 | 69,333 | 1,644 | 1,866 | 4,215 | 0 | 0 | 5 | 0 |
| GC | 2025 | 351,218 | 70,699 | 69,536 | 1,163 | 1,363 | 3,338 | 0 | 0 | 5 | 0 |
| GC | 2026 | 251,708 | 50,752 | 49,711 | 1,041 | 1,189 | 2,494 | 0 | 0 | 4 | 0 |
| NQ | 2010 | 177,590 | 40,540 | 27,651 | 12,889 | 15,487 | 28,841 | 0 | 0 | 3 | 658 |
| NQ | 2011 | 320,497 | 70,463 | 52,915 | 17,548 | 21,007 | 36,245 | 0 | 0 | 4 | 1,177 |
| NQ | 2012 | 319,424 | 70,106 | 52,160 | 17,946 | 21,390 | 35,279 | 0 | 0 | 4 | 1,117 |
| NQ | 2013 | 311,076 | 68,798 | 50,556 | 18,242 | 21,932 | 38,276 | 0 | 0 | 4 | 744 |
| NQ | 2014 | 311,758 | 68,137 | 51,497 | 16,640 | 19,985 | 33,491 | 0 | 0 | 4 | 729 |
| NQ | 2015 | 330,049 | 70,629 | 57,274 | 13,355 | 15,990 | 27,554 | 0 | 0 | 4 | 542 |
| NQ | 2016 | 336,310 | 70,087 | 60,967 | 9,120 | 10,630 | 18,066 | 0 | 0 | 4 | 1 |
| NQ | 2017 | 341,495 | 69,804 | 64,110 | 5,694 | 6,485 | 11,275 | 0 | 0 | 4 | 0 |
| NQ | 2018 | 349,186 | 70,043 | 69,383 | 660 | 833 | 4,295 | 0 | 0 | 4 | 35 |
| NQ | 2019 | 349,857 | 70,004 | 69,853 | 151 | 398 | 4,069 | 0 | 0 | 4 | 1 |
| NQ | 2020 | 349,678 | 70,150 | 69,762 | 388 | 718 | 5,852 | 0 | 0 | 4 | 2 |
| NQ | 2021 | 353,414 | 70,695 | 70,636 | 59 | 182 | 1,876 | 0 | 0 | 4 | 0 |
| NQ | 2022 | 354,116 | 70,827 | 70,808 | 19 | 19 | 19 | 0 | 0 | 4 | 0 |
| NQ | 2023 | 353,394 | 70,689 | 70,638 | 51 | 51 | 51 | 0 | 0 | 4 | 0 |
| NQ | 2024 | 354,982 | 71,013 | 70,940 | 73 | 77 | 83 | 0 | 0 | 4 | 0 |
| NQ | 2025 | 352,519 | 70,518 | 70,451 | 67 | 68 | 714 | 0 | 0 | 4 | 0 |
| NQ | 2026 | 254,729 | 50,955 | 50,913 | 42 | 44 | 46 | 0 | 0 | 3 | 0 |

\* These are observed absences between published bars within the inherited session label. Without a versioned historical exchange calendar they are not asserted to be vendor data loss; they may be no-trade intervals, venue closures, or unknown absences.

Duplicate source timestamps, invalid source OHLC rows, timestamp-order failures, New York five-minute alignment failures, and raw-price tick-alignment failures were all zero; otherwise the build would have failed.

## Spot checks

### ES

Boundary buckets:

- 19:30 NY → `2024-01-02T00:30:00.000000000Z`; source opens `2024-01-02T00:30:00.000000000Z` through `2024-01-02T00:34:00.000000000Z` (5 bars).
- 20:30 NY → `2024-01-02T01:30:00.000000000Z`; source opens `2024-01-02T01:30:00.000000000Z` through `2024-01-02T01:34:00.000000000Z` (5 bars).
- 03:00 NY → `2024-01-02T08:00:00.000000000Z`; source opens `2024-01-02T08:00:00.000000000Z` through `2024-01-02T08:04:00.000000000Z` (5 bars).
- 04:00 NY → `2024-01-02T09:00:00.000000000Z`; source opens `2024-01-02T09:00:00.000000000Z` through `2024-01-02T09:04:00.000000000Z` (5 bars).
- 09:30 NY → `2024-01-02T14:30:00.000000000Z`; source opens `2024-01-02T14:30:00.000000000Z` through `2024-01-02T14:34:00.000000000Z` (5 bars).
- 10:25 NY → `2024-01-02T15:25:00.000000000Z`; source opens `2024-01-02T15:25:00.000000000Z` through `2024-01-02T15:29:00.000000000Z` (5 bars).
- 10:30 NY → `2024-01-02T15:30:00.000000000Z`; source opens `2024-01-02T15:30:00.000000000Z` through `2024-01-02T15:34:00.000000000Z` (5 bars).

DST transition windows:

- spring_2024: 2,760 bars; 0 NY alignment failures.
- fall_2024: 2,760 bars; 0 NY alignment failures.

Holiday / early-close observation checks (not calendar certification):

- session `2024-11-28`: 228 bars, 0 partial; `2024-11-27T23:00:00.000000000Z` to `2024-11-28T17:55:00.000000000Z`.
- session `2024-11-29`: 231 bars, 0 partial; `2024-11-28T23:00:00.000000000Z` to `2024-11-29T18:10:00.000000000Z`.

Roll check: `2024-03-12T22:00:00.000000000Z` contains the roll marker; `ESM4` → `ESM4`, mixed-contract=false, mixed-adjustment=false.

### GC

Boundary buckets:

- 19:30 NY → `2024-01-02T00:30:00.000000000Z`; source opens `2024-01-02T00:30:00.000000000Z` through `2024-01-02T00:34:00.000000000Z` (5 bars).
- 20:30 NY → `2024-01-02T01:30:00.000000000Z`; source opens `2024-01-02T01:30:00.000000000Z` through `2024-01-02T01:34:00.000000000Z` (5 bars).
- 03:00 NY → `2024-01-02T08:00:00.000000000Z`; source opens `2024-01-02T08:00:00.000000000Z` through `2024-01-02T08:04:00.000000000Z` (5 bars).
- 04:00 NY → `2024-01-02T09:00:00.000000000Z`; source opens `2024-01-02T09:00:00.000000000Z` through `2024-01-02T09:04:00.000000000Z` (5 bars).
- 09:30 NY → `2024-01-02T14:30:00.000000000Z`; source opens `2024-01-02T14:30:00.000000000Z` through `2024-01-02T14:34:00.000000000Z` (5 bars).
- 10:25 NY → `2024-01-02T15:25:00.000000000Z`; source opens `2024-01-02T15:25:00.000000000Z` through `2024-01-02T15:29:00.000000000Z` (5 bars).
- 10:30 NY → `2024-01-02T15:30:00.000000000Z`; source opens `2024-01-02T15:30:00.000000000Z` through `2024-01-02T15:34:00.000000000Z` (5 bars).

DST transition windows:

- spring_2024: 2,760 bars; 0 NY alignment failures.
- fall_2024: 2,760 bars; 0 NY alignment failures.

Holiday / early-close observation checks (not calendar certification):

- session `2024-11-28`: 124 bars, 124 partial; `2024-11-27T23:00:00.000000000Z` to `2024-11-28T18:55:00.000000000Z`.
- session `2024-11-29`: 249 bars, 1 partial; `2024-11-28T23:00:00.000000000Z` to `2024-11-29T19:40:00.000000000Z`.

Roll check: `2024-01-30T23:00:00.000000000Z` contains the roll marker; `GCJ4` → `GCJ4`, mixed-contract=false, mixed-adjustment=false.

### NQ

Boundary buckets:

- 19:30 NY → `2024-01-02T00:30:00.000000000Z`; source opens `2024-01-02T00:30:00.000000000Z` through `2024-01-02T00:34:00.000000000Z` (5 bars).
- 20:30 NY → `2024-01-02T01:30:00.000000000Z`; source opens `2024-01-02T01:30:00.000000000Z` through `2024-01-02T01:34:00.000000000Z` (5 bars).
- 03:00 NY → `2024-01-02T08:00:00.000000000Z`; source opens `2024-01-02T08:00:00.000000000Z` through `2024-01-02T08:04:00.000000000Z` (5 bars).
- 04:00 NY → `2024-01-02T09:00:00.000000000Z`; source opens `2024-01-02T09:00:00.000000000Z` through `2024-01-02T09:04:00.000000000Z` (5 bars).
- 09:30 NY → `2024-01-02T14:30:00.000000000Z`; source opens `2024-01-02T14:30:00.000000000Z` through `2024-01-02T14:34:00.000000000Z` (5 bars).
- 10:25 NY → `2024-01-02T15:25:00.000000000Z`; source opens `2024-01-02T15:25:00.000000000Z` through `2024-01-02T15:29:00.000000000Z` (5 bars).
- 10:30 NY → `2024-01-02T15:30:00.000000000Z`; source opens `2024-01-02T15:30:00.000000000Z` through `2024-01-02T15:34:00.000000000Z` (5 bars).

DST transition windows:

- spring_2024: 2,760 bars; 0 NY alignment failures.
- fall_2024: 2,760 bars; 0 NY alignment failures.

Holiday / early-close observation checks (not calendar certification):

- session `2024-11-28`: 228 bars, 0 partial; `2024-11-27T23:00:00.000000000Z` to `2024-11-28T17:55:00.000000000Z`.
- session `2024-11-29`: 231 bars, 0 partial; `2024-11-28T23:00:00.000000000Z` to `2024-11-29T18:10:00.000000000Z`.

Roll check: `2024-03-12T22:00:00.000000000Z` contains the roll marker; `NQM4` → `NQM4`, mixed-contract=false, mixed-adjustment=false.

## Roll and adjustment provenance

- Source manifest: `catalog/datasets/volume_lead_back_adjusted_v1.json` (`5500ac1e472c48b0f31b11c6586354dc700e4ba2ef526ebef5fa05582b228ce8`)
- Roll schedule: `data/curated/continuous/1m/roll=volume_lead_v1/roll_schedule.parquet` (`0149b99b75da1138454e5face6516184ace3fef819b324183448c678460621b0`)
- Adjustment schedule: `data/curated/continuous/1m/roll=volume_lead_v1/adjustment=prior_session_close_additive_v1/adjustment_schedule.parquet` (`52aeef2bd1e04aadad0a1eb2efdd81165b4c4880025c432df80870955be64027`)
- Adjustment factors: `data/curated/continuous/1m/roll=volume_lead_v1/adjustment=prior_session_close_additive_v1/adjustment_factors.parquet` (`7682affe39711fabc09bb1424253d6a576457b54f1e869d35d393bf2db542b0b`)
- Phase 2 adjustment snapshot/as-of: `2026-09-20T19:05:09.246197+00:00`
- Roll selection is prior-day Databento volume rank 0, effective at the mapped Globex session boundary.
- Back-adjustment is cumulative additive prior-shared-session-close adjustment. Historical bars use later roll information and are not point-in-time certified.

## Calendar and absence classification

No authoritative versioned historical CME product calendar was available to this build. Observed source bars were therefore preserved even in the nominal 17:00–18:00 America/New_York maintenance window, including older schedule regimes. No closure was manufactured or filled. Provider condition reports, including degraded dates and dates with no published records, remain pinned through the Phase 2 manifest.

## Determinism and validation

- Request SHA-256: `7ca07c4e7a085eced06fdff51ba95af66f953ed2ce4a10def423c1edd982c902`
- Canonical request/config SHA-256: `1ac0baa7f46817cce8a1293a3996f91ee423f1ca1739fa9e69f3997b0e45edc5`
- Partitions independently replayed: 51
- Deterministic replay: true
- Phase 2 lineage verified: true
- Synthetic market rows: 0

## PyArrow loader

```python
from pathlib import Path
import pyarrow.dataset as ds

root = Path("/Users/ppanati/Documents/projects/abacus-bhishma/data/features/bars/5m/feature_set=dridr_ohlcv_5m/version=1.0.0")
bars = ds.dataset(root, format="parquet", partitioning="hive")

# Load one product and a bounded period. Partition filters prune files.
table = bars.to_table(
    filter=(ds.field("product") == "ES") & (ds.field("year") == 2024),
    columns=[
        "ts_event", "session_date", "product", "open", "high", "low",
        "close", "volume", "raw_symbol", "price_adjustment",
        "source_bar_count", "is_partial_bar", "contains_roll",
    ],
)

# OHLC and price_adjustment are exact int64 fixed-point values at scale 1e-9.
# Convert only at the consumer boundary when floats are required:
close_float = table["close"].to_numpy() * 1e-9
print(table.num_rows, table["ts_event"][0], close_float[0])
```

## Known limitations

- The source is a final backward-adjusted snapshot. Historical adjusted prices incorporate later rolls and are not point-in-time certified or directly tradable.
- This delivery uses the source-observed session_date and preserves observed bars, but it does not certify historical CME holiday, early-close, or maintenance calendars.
- Databento omits OHLCV intervals with no trades. Missing source minutes remain absent; partial five-minute bars are flagged rather than filled.
- The volume-led roll and additive adjustment methodology is reproducible but is not claimed to match TradingView exactly.
- A future Phase 2 roll can change all earlier adjusted prices. Consumers must pin this manifest and its checksums.

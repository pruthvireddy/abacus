# Range XV long-history import and gap audit

## Clock correction after import

On 2026-09-24, all fourteen enhanced Range XV CSVs were normalized in place
from an **inferred fixed UTC−04:00 export clock** to `America/New_York` wall
time. Winter bar timestamps moved back one hour; summer timestamps did not
move. The original `source_timestamp` column, five-column files in `source/`,
bar order, OHLC values, and session-date coverage remain unchanged. The
[clock migration record](migration/range-xv-clock-normalization-20260924.json)
pins before/after hashes. ATAS timezone settings have not been independently
verified. Times below that describe the *original import* remain raw export
clock unless explicitly identified otherwise.

The seven ATAS downloads from `/Users/ppanati/Documents/Atas-Exports` were
imported as a new Sahadeva input snapshot at
`data/range_xv/20191101_20260924/`. Its `source/` directory retains the
downloaded CSV bytes under consistent names; `enhanced/` uses the existing
Range XV research schema, including inferred session dates and next-bar-start
completion proxies. The [tracked input manifest](data/range_xv_long_history_20191101_20260924.json)
records every path, row count, timestamp range, and SHA-256 hash. The
[import script](../scripts/import-range-xv-20260924.py) records the transformation.

The names use `<product>_rangexv_<setting>t_<first-session>_<last-session>.csv`.
They use product labels rather than the old `U6`/`Z6` contract labels because
these exports span 2019–2026 and do not identify their underlying contract or
roll treatment. All raw timestamps run from **2019-10-31 18:00:00** to a
setting-specific time on **2026-09-23 or 2026-09-24**. With the existing 18:00
session-date proxy, all seven run from **2019-11-01 through 2026-09-24**.
The export timezone and exact bar-completion time are unverified.

| Product | Setting | Downloaded name | Canonical name | Rows |
|---|---:|---|---|---:|
| ES | 4 ticks | `es-4rxv.csv` | `ES_rangexv_4t_20191101_20260924.csv` | 1,281,962 |
| ES | 5 ticks | `es-5xrv.csv` | `ES_rangexv_5t_20191101_20260924.csv` | 885,222 |
| ES | 6 ticks | `es-6rxv.csv` | `ES_rangexv_6t_20191101_20260924.csv` | 647,911 |
| GC | 6 ticks | `gc-6rxv.csv` | `GC_rangexv_6t_20191101_20260924.csv` | 1,661,279 |
| GC | 10 ticks | `gc-10rxv.csv` | `GC_rangexv_10t_20191101_20260924.csv` | 737,194 |
| NQ | 10 ticks | `nq-10rxv.csv` | `NQ_rangexv_10t_20191101_20260924.csv` | 4,646,126 |
| NQ | 20 ticks | `nq-20-rxv.csv` | `NQ_rangexv_20t_20191101_20260924.csv` | 1,343,643 |

## Replacement boundary

The older seven enhanced files and their manifest now carry the same clock
normalization as the longer files. The compatibility CSV links under
`legacy/sahadeva/data/` resolve to those files; the compatibility manifest
resolves to the current manifest. Completed runs remain unchanged and retain
their original input hashes. New work can use the longer snapshot after reviewing
the gaps below; a new study or run must pin its manifest and file hashes
explicitly. It does not contain **GC 20 RXV**, while it adds
**ES 4 RXV**. The frozen [study 07 plan](../studies/07_range_xv_edge_candidates/plan.md)
requires GC 20 RXV, so its existing three-product protocol cannot simply be
pointed at this snapshot.

## Coverage and observed gaps

- All six overlapping settings contain every inferred session date found in
  their older 2024–2026 file. ES and NQ bar sequences match their older
  counterparts on 534 complete shared sessions; the older 2026-09-08 session
  was truncated and the new exports extend it.
- ES and NQ have 1,783 inferred session dates. GC 6 and GC 10 each have 1,780.
  Relative to ES/NQ, both GC files lack 2021-04-02, 2023-04-07, and
  2026-04-03. The files alone cannot distinguish market closure from missing
  export data. The largest separation between successive observed session
  dates is three absent calendar dates.
- The new GC files **are not exact extensions** of the older GC files.
  Including the formerly partial 2026-09-08 session, GC 6 differs on 166 of
  534 shared sessions and GC 10 differs on 119 of 534. Some differences are
  one-second timestamp shifts; some include fewer or more bars.
- The clearest GC data gap is the 2026-03-19 session. GC 6 has no new bar start
  between **10:12:45 and 11:45:32** (1h32m47s); the older file has 1,555
  bars strictly inside that interval. GC 10 has no new bar start between
  **10:12:45 and 15:01:20** (4h48m35s); the older file has 1,511 bars inside.
  The new files have 2,609 fewer GC 6 bars and 2,042 fewer GC 10 bars over
  that session. These are raw export-clock times, not verified Eastern times.
- Other shared GC sessions with substantial new-file row deficits include
  2026-02-20 (GC 6: 462 fewer; GC 10: 219 fewer), 2026-01-28
  (332; 157), 2026-02-04 (271; 153), and 2026-04-02 (217; 105).
  A row-count difference alone does not prove a continuous time gap, but
  these dates should be inspected before using the new GC series for research.

Before 2024-08-14 there is no older Range XV export in this workspace for a
bar-by-bar comparison. Because Range XV bars are event-driven, a quiet interval
in one file alone does not establish whether bars are missing.

All 11,203,337 source rows have valid timestamps, five columns, finite
tick-aligned prices, and valid OHLC ordering. No timestamps regress. A
synthetic same-second/session-boundary test showed that the import converter
produces the same enhanced bytes as the archived converter. The existing
study 07 loader read samples from all seven enhanced files.

The large CSVs are ignored by Git and need separate backup. The tracked
manifest preserves their expected hashes; it does not contain the CSV bytes.

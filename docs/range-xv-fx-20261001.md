# Range XV FX import — October 1, 2026

Eight ATAS currency-futures OHLC exports from Downloads are retained as a new,
separate input snapshot at `data/range_xv/fx_20170721_20261001/`. The snapshot
contains **2,002,278 bars**. Raw export timestamps begin on July 20, 2017; the
inferred session-date range is **2017-07-21 through 2026-10-01**. All eight
files contain the same **2,377 observed session dates**. October 1 is partial;
the files were exported at different times that morning.

The [tracked manifest](data/range_xv_fx_20170721_20261001.json) records product
labels, settings, original filenames and download locations, source/enhanced
hashes and sizes, row counts, clock assumptions, completion statuses, quality
flags, coverage, exact invocation, and retained conversion/environment sources.
Its bytes match the physical `range_xv_exports_manifest.json` in the snapshot.
This is an imported research-input snapshot, with no strategy study or public
web publication attached to it.

## Files and naming

Both `source/` and `enhanced/` use
`<product>_rangexv_<setting>t_<first-session>_<last-session>.csv`. For example,
`6E_rangexv_4t_20170721_20261001.csv`. Uppercase product labels replace the
mixed case of the original filenames. Labels and settings come from filenames;
the exports do not independently verify the ATAS chart configuration.

| Product | Instrument | Setting | Downloaded filename | Rows | Repeated records | Zero-range bars |
|---|---|---:|---|---:|---:|---:|
| 6E | Euro | 4 | `6E-4RXV.csv` | 435,603 | 13 | 19 |
| 6E | Euro | 5 | `6E-5rxv.csv` | 303,314 | 3 | 9 |
| 6B | British pound | 4 | `6b-4rxv.csv` | 202,295 | 6 | 21 |
| 6B | British pound | 5 | `6b-5rxv.csv` | 142,007 | 3 | 16 |
| 6J | Japanese yen | 4 | `6J-4rxv.csv` | 253,253 | 6 | 32 |
| 6J | Japanese yen | 5 | `6j-5rxv.csv` | 178,148 | 8 | 17 |
| 6S | Swiss franc | 4 | `6s-4rxv.csv` | 283,389 | 1 | 58 |
| 6S | Swiss franc | 5 | `6s-5rxv.csv` | 204,269 | 1 | 33 |
| **Total** | | | | **2,002,278** | **41** | **205** |

`source/` preserves the original downloaded bytes exactly, including line
endings, timestamp strings, price formatting, and row order. Every source row
appears once in `enhanced/`; no duplicates, flat bars, or final rows are removed.
The source OHLC prices are not adjusted during import. The files do not disclose
whether the source chart used price adjustment or which contracts/rolls it used;
this import does not certify them as unadjusted execution prices.

## Columns and timing labels

The raw CSVs have no header and use `;` as their delimiter. Each row has exactly
five columns: timestamp, open, high, low, close. Timestamps use
`YYYY-DD-MM HH:MM:SS`, so `2026-01-10` means October 1, 2026. **Volume is absent**;
so are trade counts, bid/ask or delta, timezone, contract/roll identifiers, and
exact bar-completion time. These fields are not inferred or fabricated.

Enhanced CSVs use the same eleven-column layout as the
[existing Range XV files](../data/range_xv/README.md):

| Column | Meaning |
|---|---|
| `source_row` | One-based row position in the headerless original export. |
| `source_timestamp` | Verbatim original ATAS timestamp, in the raw export clock. |
| `bar_start_timestamp` | Opening-time interpretation converted to inferred New York wall time, in `YYYY-MM-DD HH:MM:SS`. |
| `bar_completion_timestamp_proxy` | Next row's New York bar-start time, only within the same inferred session. |
| `bar_duration_seconds_proxy` | Whole-second difference between those starts; a timing proxy. |
| `completion_proxy_status` | Whether a next-start completion proxy is usable. |
| `session_date_proxy` | New York calendar date, assigning starts at or after 18:00 to the next date. |
| `open`, `high`, `low`, `close` | Verbatim source OHLC strings, preserving precision and trailing zeros. |

Completion statuses retain the existing meanings:

- `next_bar_start_proxy`: the next bar starts later in the same session.
- `next_bar_start_same_second`: the next bar starts in the same recorded second;
  duration is `0`, with original row order preserved and subsecond time unknown.
- `unavailable_session_boundary`: the next bar belongs to another session;
  completion and duration are empty.
- `unavailable_export_end`: the final export row has no successor; completion
  and duration are empty, and that bar may still have been forming.

Observed raw session openings cluster around **19:00 in winter and 18:00 in
summer**, matching the earlier clock inference. This importer interprets the
raw clock as fixed UTC-04:00 and converts derived timestamps to
`America/New_York`, following the
[September clock method](migration/range-xv-clock-normalization-20260924.json).
Winter derived times move back one hour; summer times remain the same.
The original source timestamp never changes. The ATAS timezone/session
configuration remains unverified, and the enhanced times are naive wall-time
strings with their zone declared by the manifest.

Completion is a next-bar-start proxy, not the exact last-trade time. Completed
OHLC must not be treated as information available at its opening timestamp.
Same-second ordering does not establish subsecond availability; the last row
has no observable completion proxy. Research must declare its handling of
these statuses and pin this snapshot's manifest and enhanced-file hashes.

## Quality records and limits

Every input row passed five-column, timestamp-layout/calendar, chronological
order, finite positive-price, and OHLC-order checks. The converter then checked
every enhanced row against the retained source and derived-label rules. All
prices, source timestamp strings, and original row positions are preserved.

The `quality/` directory contains two CSVs per product/setting:

- `<canonical-stem>_flags.csv` identifies `source_row`, source timestamp,
  derived bar-start time, and flag. `repeated_timestamp_ohlc_record` flags later
  occurrences of the same timestamp/OHLC tuple; `zero_range_bar` flags high
  equal to low. These are review flags, not automatic exclusions. A second-level
  timestamp cannot prove whether identical records represent duplicate exports
  or distinct bars.
- `<canonical-stem>_sessions.csv` records each inferred session's row count,
  first/last source rows and bar-start times, and export-edge status. The final
  session is `export_end_session_partial`; other session completeness remains
  unverified, including the first session.

The manifest also records opening-clock distributions, same-session intervals
of at least one hour, and the three largest such intervals per file. Long gaps
between event-driven Range XV bars do not alone establish missing data. Equal
session-date sets across the eight exports do not prove complete intraday
coverage or compliance with an independently verified exchange calendar.

The older ES/GC/NQ snapshots, their manifests, the clock migration record, and
the hash-pinned Range XV README are unchanged. The new manifest records those
historical hashes as protection checks. Existing legacy links and sealed runs
continue to refer to their previous inputs.

## Import and verification

The [batch orchestrator](../scripts/import-range-xv-20261001.py) uses the
[Bhishma converter](../packages/bhishma/src/abacus_bhishma/range_xv.py).
Storage resolves through the [workspace path configuration](../config/paths.example.toml);
this in-Abacus import requires publication and workspace roots to be the same.
It stages new output under a unique `work/import-range-xv-fx-20261001-*`
directory, verifies copied source hashes and all enhanced rows, and only then
stores the snapshot at its final path. Existing destinations or tracked
manifests are never overwritten.

The snapshot retains the executed converter, batch script, path resolver,
`uv.lock`, and system New York timezone file under `provenance/`, each with a
manifest hash. Python/platform and Git revision/dirty state are recorded.
The local dataset README is also included in the artifact hash inventory.
The original downloads are removed only after stored artifacts verify and
their current hashes still match the imported sources, completing the requested
move. Downloads are not needed for later verification.

Initial import (do not rerun into the completed snapshot):

```sh
./scripts/uv run --locked python scripts/import-range-xv-20261001.py import --source-dir /Users/ppanati/Downloads
```

Read-only verification of both manifests, every stored artifact, historical
protection hashes, and all source/enhanced row pairs:

```sh
./scripts/uv run --locked python scripts/import-range-xv-20261001.py verify
```

Focused synthetic checks cover the unusual day/month format, winter/summer and
midnight conversion, same-second ordering, session boundaries, final-row
handling, anomaly retention, malformed inputs, and overwrite protection:

```sh
./scripts/uv run --locked python -m unittest discover -s packages/bhishma/tests -p test_range_xv.py
```

The tracked manifest and this guide retain metadata, not bulk CSV contents.
Back up `data/range_xv/fx_20170721_20261001/` separately; it is excluded from
ordinary Git history.

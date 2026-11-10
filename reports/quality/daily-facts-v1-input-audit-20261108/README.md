# Daily Facts v1 input audit November 8 2026

ES and NQ have complete retained daytime inputs on every eligible date in the
common supported period. GC daytime coverage is also high, while strict full-Globex
coverage is substantially lower. Daily Facts should preserve independent window
readiness so overnight gaps do not discard usable daytime observations.

This is an audit of existing selected inputs for the [Daily Facts v1 design](../../../docs/daily-facts-v1-design.md).
It produces coverage and integrity evidence, not a Daily Facts release or new study
findings. The production builder, database, API and website remain unimplemented.

## Coverage by window in the common period

Period: June 28, 2021 through September 18, 2026, inclusive. Denominators are
weekdays supported by the pinned calendar after its holiday/shortened-day exclusions.
ES/NQ have 1,303 candidate sessions; GC has 1,306 because its exclusion rules differ.
For direct cross-asset comparisons, use the separately saved joint candidate set.

A complete window has every expected minute exactly once, valid OHLCV rows and
one contract. Missing minutes are not filled. Percentages describe retained-grid
coverage, not corruption rates, historical live availability or strategy validity.

| Window | ES | NQ | GC |
|---|---|---|---|
| globex | 1,045 / 1,303 (80.2%) | 1,184 / 1,303 (90.9%) | 423 / 1,306 (32.4%) |
| overnight | 1,047 / 1,303 (80.4%) | 1,185 / 1,303 (90.9%) | 533 / 1,306 (40.8%) |
| rth | 1,303 / 1,303 (100.0%) | 1,303 / 1,303 (100.0%) | 1,272 / 1,306 (97.4%) |
| or15 | 1,303 / 1,303 (100.0%) | 1,303 / 1,303 (100.0%) | 1,285 / 1,306 (98.4%) |
| first60 | 1,303 / 1,303 (100.0%) | 1,303 / 1,303 (100.0%) | 1,280 / 1,306 (98.0%) |
| last60 | 1,303 / 1,303 (100.0%) | 1,303 / 1,303 (100.0%) | 1,272 / 1,306 (97.4%) |

Opening-price coverage is checked separately from final aggregate readiness.
RTH opening minutes are present and valid on 1,303/1,303 ES and NQ candidates,
and 1,298/1,306 GC candidates. Later missing minutes do not erase an available open.
The seven-day preopen volatility lookup is valid on every asset's common-period
candidate date: VIX 1,303/1,303, VXN 1,303/1,303 and GVZ 1,306/1,306.

## Consequence of requiring a complete Globex session

| Asset | Complete RTH windows | Also complete Globex | Usable RTH windows discarded |
|---|---|---|---|
| ES | 1,303 | 1,045 | 258 |
| NQ | 1,303 | 1,184 | 119 |
| GC | 1,272 | 423 | 849 |

GC opening-range completeness is 1,285 sessions; imposing a full-Globex gate
would retain 423 and discard 862 of those complete opening ranges. A study may
choose a retrospective whole-day sample, but the shared input layer should not
apply it to every fact.

Globex VWAP checkpoints require coverage from the evening anchor to the relevant
checkpoint. Complete input grids through RTH end exist on ES 1,047/1,303,
NQ 1,185/1,303 and GC 533/1,306 candidate dates. RTH-only VWAP can use the much
larger complete RTH sample. No VWAP values were calculated in this audit.

## Annual coverage in the common period

Counts are complete/candidate sessions. The 2021 period begins June 28; 2026 ends
September 18. Full six-window annual detail is in [coverage_by_year.csv](coverage_by_year.csv).

| Year | ES Globex | ES RTH | NQ Globex | NQ RTH | GC Globex | GC RTH |
|---|---|---|---|---|---|---|
| 2021 (partial) | 102 / 130 | 130 / 130 | 116 / 130 | 130 / 130 | 15 / 130 | 126 / 130 |
| 2022 | 240 / 250 | 250 / 250 | 237 / 250 | 250 / 250 | 55 / 250 | 243 / 250 |
| 2023 | 155 / 248 | 248 / 248 | 217 / 248 | 248 / 248 | 35 / 249 | 242 / 249 |
| 2024 | 160 / 249 | 249 / 249 | 214 / 249 | 249 / 249 | 63 / 250 | 245 / 250 |
| 2025 | 218 / 247 | 247 / 247 | 227 / 247 | 247 / 247 | 168 / 248 | 243 / 248 |
| 2026 (partial) | 170 / 179 | 179 / 179 | 173 / 179 | 179 / 179 | 87 / 179 | 173 / 179 |

## Retained history and calendar restrictions

All selected minute files cover session dates from June 7, 2010 through September
18, 2026. There are 4,250 weekday inventory dates per asset, including dates with
no source rows. The source contains one additional Sunday observation per asset,
assigned to August 5, 2018; these are excluded from weekday coverage denominators.

| Asset | Minute rows | Verified partitions | Observed session dates including Sunday | Invalid OHLC rows |
|---|---|---|---|---|
| ES | 5,694,142 | 17 | 4,195 | 0 |
| NQ | 5,520,074 | 17 | 4,195 | 0 |
| GC | 5,651,836 | 17 | 4,191 | 0 |

All three products have zero inspected null cells, zero nonincreasing timestamp
pairs and zero rows outside the assigned date envelope. Contract identity is
checked per window. The source also retains rows outside the nominal 18:00–17:00
Globex interval: ES 24,656; NQ 19,668; GC 17,814. They match the publication's
recorded maintenance-window counts and are excluded by the nominal window filters;
no source rows are changed.

The pinned calendar supports ES/NQ from June 28, 2021 and GC from September 21,
2015. It excludes 62 ES/NQ and 59 GC holiday/shortened dates in the common period.
Across all product-supported history, the denominators are ES/NQ 1,303 and GC 2,748.

| Window | ES supported history | NQ supported history | GC supported history |
|---|---|---|---|
| globex | 1,045 / 1,303 | 1,184 / 1,303 | 841 / 2,748 |
| overnight | 1,047 / 1,303 | 1,185 / 1,303 | 1,098 / 2,748 |
| rth | 1,303 / 1,303 | 1,303 / 1,303 | 2,666 / 2,748 |
| or15 | 1,303 / 1,303 | 1,303 / 1,303 | 2,707 / 2,748 |
| first60 | 1,303 / 1,303 | 1,303 / 1,303 | 2,691 / 2,748 |
| last60 | 1,303 / 1,303 | 1,303 / 1,303 | 2,668 / 2,748 |

For inventory only, these are the complete nominal-window counts over all 4,250
weekdays, including unsupported regimes and holiday dates. They are not an
endorsed historical Daily Facts sample:

| Window | ES nominal inventory | NQ nominal inventory | GC nominal inventory |
|---|---|---|---|
| globex | 1,045 / 4,250 | 1,184 / 4,250 | 856 / 4,250 |
| overnight | 1,850 / 4,250 | 1,881 / 4,250 | 1,153 / 4,250 |
| rth | 4,053 / 4,250 | 4,045 / 4,250 | 3,977 / 4,250 |
| or15 | 4,181 / 4,250 | 4,180 / 4,250 | 4,119 / 4,250 |
| first60 | 4,179 / 4,250 | 4,168 / 4,250 | 4,093 / 4,250 |
| last60 | 4,057 / 4,250 | 4,056 / 4,250 | 3,995 / 4,250 |

Earlier ES/NQ restrictions relate to the historical 16:15–16:30 pause; GC's earlier
restriction relates to the historical 17:15 close. A future one-minute calendar
could separately qualify unaffected daytime windows. This audit preserves the
existing restrictions and does not change calendar eligibility.

## Shared-date coverage and missing-minute examples

On the 1,303 dates jointly eligible for all three assets, all-three completeness
is Globex 359, overnight 445, RTH 1,269, opening 15 minutes 1,282, first hour 1,277
and last hour 1,269. See [common_asset_intersections.csv](common_asset_intersections.csv).

The largest eligible common-period GC Globex gap is May 31, 2023: 135 observed
minutes and 1,245 absent expected minutes. GC's RTH window that day has 62 observed
and 248 absent minutes. July 30, 2021 has 1,185 absent Globex minutes and 223 absent
RTH minutes. Other severe examples occur near month-end. These are timestamp
absences in the selected contract publication; this audit does not establish
whether absent no-trade minutes, liquidity/contract selection or source delivery
caused them. Review those possibilities before weakening completeness rules or
changing the contract-selection methodology.

Many incomplete full sessions miss only a few minutes. Among the incomplete
common-period Globex sessions, ES has 147 with exactly one absent minute, NQ 85
and GC 245. Both small and severe gaps remain explicit under v1's strict proposal.
Selected diagnostics are in [coverage_examples.csv](coverage_examples.csv).

## Daily context inputs

The six relevant daily-context Parquet files and original source CSVs match their
release hashes. Their last confirmed date is September 23, 2026. ES/NQ/GC daily
chart exports are inventoried as alternative context only; they are not substituted
for the selected minute price source.

| Series | Confirmed rows | First source day | Last source day |
|---|---|---|---|
| ES | 7,344 | 1997-09-09 | 2026-09-23 |
| NQ | 6,887 | 1999-06-30 | 2026-09-23 |
| GC | 13,011 | 1975-01-02 | 2026-09-23 |
| VIX | 9,268 | 1990-01-03 | 2026-09-23 |
| VXN | 6,448 | 2001-01-24 | 2026-09-23 |
| GVZ | 4,562 | 2008-08-01 | 2026-09-23 |

VIX and GVZ preopen lookup is valid on all 4,250 weekday inventory dates. VXN is
valid on 4,247; February 20–22, 2017 select a February 10 observation older than
seven elapsed days and are marked stale. These dates precede the common pilot.
Logical source availability and the modeled preopen lookup do not certify
historical provider vintages or actual historical access.

## Audit provenance and verification

Execution: 2026-11-08T23:06:39.270449+00:00 to 2026-11-08T23:06:45.423210+00:00.
The existing locked environment ran without synchronization: Python
3.11.17, PyArrow 25.0.1,
Pandas 2.3.3 and NumPy 2.4.6.

- All 51 selected minute partitions match recorded byte sizes and SHA-256 values.
- The input inventory hashes 68 files, including manifests, definitions, calendar,
  relevant daily-context partitions and their original source CSVs. Supporting
  definitions without a recorded release digest are identified separately in
  [input_verification.csv](input_verification.csv).
- All audited input hashes were unchanged after the scan.
- The audit passed 21 synthetic checks covering window sizes, timezone conversion,
  endpoint semantics, missing/duplicate/off-grid rows, contract identity and
  independent opening readiness.
- 42 sampled source-window comparisons independently reconstruct Python
  timestamp sets and reconcile missing counts and readiness. See
  [independent_source_checks.csv](independent_source_checks.csv).
- Minute-row totals reconcile to the publication manifest. Full numerical facts,
  source vendor records, calendar certification and study conclusions are outside
  this audit.

The minute manifest is pinned to
`00757f5fc8278e75744d7adfaddc688be588d619d82b1dc1811aa60f21b7e5d4`;
the daily-context manifest to
`b7395d6ec2a3263e6f17b2ed95d22ea235d543a01e5b7f850eff81604ba6ce8f`.
[summary.json](summary.json) records the calendar/source/lock hashes, source Git
identity and dirty status, environment, exact invocation and all summary values.
[audit_inputs.py](audit_inputs.py) is the saved audit-only script, not production
Daily Facts implementation. [audit.log](audit.log) records its execution.

Original command, run from the workspace root:

```sh
UV_CACHE_DIR=/private/tmp/abacus-daily-facts-audit-uv-cache ./scripts/uv run --locked --no-sync python -B work/daily-facts-v1/20261108T230009Z_input_audit/audit_inputs.py --output work/daily-facts-v1/20261108T230009Z_input_audit/outputs
```

To repeat from the saved script, choose a new audit output directory under
`work/daily-facts-v1/`; the script refuses an existing output directory. Keep the
pinned inputs and producer identities when interpreting a comparison.

The complete 89,271-row session/window diagnostics and 12,750-row context lookup
inventory remain at their explicitly hashed local staging locators in
[artifact_manifest.json](artifact_manifest.json). They are regenerable audit
outputs, not a replacement for retained source data. Compact summaries and the
audit producer are saved here; bulk diagnostics are excluded from ordinary Git.

Documentation validation passed for 164 maintained guides, and all 37 registry
tests passed. The default workspace gate passed documentation, then ran 1,003
Bhishma tests and failed on two existing source-integration prerequisites: the
continuous volume-rank symbology JSON is absent, and the Phase 2 reference check
cannot obtain an ES roll-1 point-in-time definition pair in its ten-day window.
The remaining Sahadeva, legacy 01, legacy 02 and VWAP-doctor checks were not
executed by that fail-fast gate. See [workspace-check.log](workspace-check.log).
These failures do not invalidate the selected-file hash and coverage checks;
they do prevent claiming a passing default workspace gate or source rebuild readiness.

## Decisions before implementation

Keep the independent-window quality model. Use the common supported period for
an initial reproducible pilot while retaining the older-history inventory. Keep
Globex-anchored VWAP readiness separate from RTH-only facts. Review GC's severe
selected-contract gaps before considering a different source/roll policy; do not
repair or overwrite the published input. Decide whether a dedicated one-minute
calendar should admit earlier unaffected windows in a future release.

No source dataset, sealed run, catalog release, cloud resource, API or website was
created or modified by the coverage audit.

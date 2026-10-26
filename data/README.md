# Data storage

## Ownership and navigation

- [Bhishma — Data & Features](../packages/bhishma/AGENTS.md) owns `inbox/`,
  `raw/`, `staging/`, `curated/`, and `features/`, with dataset contracts in `../catalog/`.
- [Sahadeva — Research & Analysis](../packages/sahadeva/AGENTS.md) owns the
  historical inputs in `range_xv/` and retained evidence in `research/sahadeva/`.
  Stage new research output in [work](../work/README.md) and seal completed
  evidence using the [run guide](../runs/README.md).

Use the [repository map](../ARCHITECTURE.md#file-placement-and-ownership) for the
complete placement rules and the layer descriptions below for data retention.

## Storage layout

The data tree contains the physical copies used by this workspace. Bhishma's
`raw/`, `staging/`, `inbox/`, `curated/`, and `features/` directories retain their
original nesting directly under `data/`. Sahadeva inputs are in `range_xv/`;
retained historical working evidence is in `research/sahadeva/`. These are real
copied files, and the old external `data/bhishma` alias has been removed.

The configured publication root is the Abacus workspace (`.`), containing both
`catalog/` and `data/`; it is not this data directory or a package directory.
The configured legacy research root is `legacy/sahadeva`, with compatibility
links to this storage. The original project folders remain preserved but are
not required for active data access. Bulk files are ignored by Git and require
separate backups. Release versions, manifest contents, and file bytes remain
unchanged. See the [storage relocation record](../docs/migration/storage-relocation-20260922.md)
and [destination hash inventory](../docs/migration/storage-files-20260922.json).

This guide preserves the original Bhishma layer meanings below. The original
[data README](../legacy/bhishma/data-readme.md) remains an unchanged historical snapshot.
Vendor source material, rebuildable intermediate files, published datasets,
and retained research evidence have distinct retention rules.

## Layers

### `raw/`

Immutable files exactly as delivered by a provider, including manifests, checksums, query metadata, and condition reports. A vendor batch uses this path:

```text
raw/<provider>/<dataset>/<schema>/<batch-id>/
```

Never edit a file in place under `raw/`. If a vendor issues a correction, archive it as a new batch.

The current Databento definition batch preserves the original ZIP, its three support JSON files, and all 5,100 daily compressed DBN files together under its provider job ID. The `.dbn.zst` files remain compressed because the Databento reader can stream them directly; decoded or filtered derivatives belong in `staging/` or `curated/`, not beside the vendor payload.

Verniman blog captures retain desktop HTML, per-post Atom responses, linked
images, capture metadata and hashes together under
`raw/blogspot/verniman/html/<capture-id>/`. Each capture uses a new batch ID;
later edits to the same post never replace an earlier captured revision.

### `staging/`

Lossless decoded or extracted forms of raw files. Staging exists to make inspection and downstream conversion easier, but every file here must be reproducible from a raw batch.

The current `.dbn` file is the direct Zstandard decompression of its `.dbn.zst` source; no rows or metadata were transformed.

Decoded Verniman posts and extracted plan records belong in
`staging/verniman/<capture-id>/`, reproducible from the retained raw capture.
The 2.0.0 history publisher uses `staging/verniman/<crawl-id>-v2/`, and the
3.0.0 publisher uses `staging/verniman/<crawl-id>-v3/`, the 4.0.0 publisher
uses `staging/verniman/<crawl-id>-v4/`, and the 5.0.0 publisher uses
`staging/verniman/<crawl-id>-v5/`. The 6.0.0 publisher uses
`staging/verniman/<crawl-id>-v6/`, so prepared outputs
remain separate from capture identities and earlier releases.
Supplemental public-feed discovery records and explicitly identified image
thumbnail fallbacks live under `raw/blogspot/verniman/feed_discovery/<discovery-id>/`;
the collection manifest pins these alongside the original chronological crawl.
Thumbnail fallbacks do not erase failures to retrieve the full-size source images.

### `curated/`

Validated datasets with stable schemas, including symbol-mapped market data
and separately identified external source claims. Curated data has four distinct products:

- `instruments/` contains contract and symbology reference data.
- `bars/` contains contract-level bars and keeps outrights separate from spreads.
- `continuous/` contains explicitly constructed continuous futures series.
- `external_levels/` contains source-supplied narrative levels with retained
  text, revision identity and timing qualifications.

Contract-level bars use Hive-style partitions suitable for Parquet readers:

```text
curated/bars/<interval>/product=<root>/instrument_type=<outright|spread>/year=<YYYY>/part-*.parquet
```

Continuous data must add a named, versioned roll methodology and variant before year partitions, for example:

```text
curated/continuous/1m/product=ES/roll=<rule-and-version>/variant=<variant>/year=<YYYY>/part-*.parquet
```

The current Phase 1 publication is:

```text
curated/continuous/1m/product=<ES|NQ|GC>/roll=volume_lead_v1/variant=unadjusted/year=<YYYY>/part-000.parquet
curated/continuous/1m/roll=volume_lead_v1/roll_schedule.{parquet,csv}
curated/instruments/roll=volume_lead_v1/instrument_master.parquet
```

`volume_lead_unadjusted_v1` is the contract-truth layer. It selects the Databento `v.0` leader at the opening of each mapping's Globex session and copies that contract's OHLCV values without adjustment. Prices are stored as exact Databento `int64` fixed-point values at scale `1e-9`; use `abacus_bhishma.continuous_loader.price_to_float` only at the consumer boundary when floating-point prices are desired.

These outputs contain real outright-contract prices and therefore change price level at rolls. They are suitable for execution and P&L modeling and are the traceable input to the Phase 2 back-adjusted series. Back-adjusted values, indicators, and strategies do not belong in the Phase 1 paths.

The Phase 2 publication is:

```text
curated/continuous/1m/product=<ES|NQ|GC>/roll=volume_lead_v1/variant=back_adjusted/adjustment=prior_session_close_additive_v1/year=<YYYY>/part-000.parquet
curated/continuous/1m/roll=volume_lead_v1/adjustment=prior_session_close_additive_v1/adjustment_schedule.{parquet,csv}
curated/continuous/1m/roll=volume_lead_v1/adjustment=prior_session_close_additive_v1/adjustment_factors.{parquet,csv}
```

`volume_lead_back_adjusted_v1` preserves the complete Phase 1 row set and adds `price_adjustment` to OHLC only. It uses paired outgoing/incoming closes from the latest shared prior session, accumulates roll gaps backward, and leaves the latest interval unadjusted. Volume and identifiers remain identical to Phase 1.

Use Phase 2 for charts, indicators, feature engineering, and signals. Its prices are synthetic and must not be used as direct execution prices or to calculate fill-level P&L. Downstream work should pin the Phase 2 manifest because each new roll changes the historical cumulative adjustment.

The [Verniman ten-session request](../requests/fulfilled/verniman_daily_levels__1.0.0.yaml)
stores `outlooks.{parquet,csv}` and `levels.{parquet,csv}` under
`curated/external_levels/source=verniman/version=1.0.0/`; `daily_summary.csv`
is a viewing convenience. The tables preserve exact contract and source text,
both plan branches, target order, ranges, conditions and discrepancies. These
are extracted external claims, with no underlying bars or indicator computation.
Source published/updated timestamps remain claims separate from capture time.
All `available_at` values are null with `historical_availability_unverified`:
the reused historical permalinks and edited posts do not establish when the
captured 2026 plans were available before the open. Pin the release manifest
and retain bulk source/output bytes with separate backups.

The separate [Verniman year-to-date request](../requests/fulfilled/verniman_daily_levels__2.0.0.yaml)
extends collection to January 1–October 20, 2026 under
`curated/external_levels/source=verniman/version=2.0.0/`, preserving 1.0.0.
It adds `coverage.{parquet,csv}` and `issues.{parquet,csv}` beside the
outlook/level tables and viewing summary. Retain each older-link transition and
encountered post in the raw capture ledger, including unparseable or uncertain posts. Coverage lists
all calendar dates and distinguishes weekend/weekday absences from capture or
extraction failures; absence does not prove that no historical post existed.
Year assignment follows descending month/day chronology anchored to 2026,
with contract and source-update corroboration. A December 2025 boundary post
may remain raw; only in-scope 2026 outlooks enter the curated tables.
Availability remains unverified with all `available_at` values null.

The separate [Verniman 2025 request](../requests/fulfilled/verniman_daily_levels__3.0.0.yaml)
collects January 1–December 31, 2025 under
`curated/external_levels/source=verniman/version=3.0.0/`, preserving both earlier
releases. It uses the same four canonical tables and viewing summary, with a
new source-capture batch, chronological ledger and public-feed crosscheck.
The December 31, 2025 seed reuses the prior crawl's hash-pinned boundary capture
with its original timestamps; every newly traversed post receives new captures.
Year assignment follows descending month/day chronology anchored to December
31, 2025; contract delivery year does not determine the session year. In
particular, a 2026 contract in late 2025 remains a 2025 outlook when supported
by chronology. Retain the out-of-range boundary, source date disagreements,
gaps and extraction issues; all historical availability values remain null.

The separate [Verniman 2024 request](../requests/fulfilled/verniman_daily_levels__4.0.0.yaml)
collects January 1–December 31, 2024 under
`curated/external_levels/source=verniman/version=4.0.0/`, preserving the three
earlier releases. It uses the same four canonical tables and viewing summary,
with all 366 calendar dates, including February 29, recorded in coverage.
The December 31, 2024 seed reuses the prior crawl's hash-pinned boundary capture
with its original timestamps; newly traversed posts receive new source captures.
Retain the chronological ledger, public-feed crosscheck, older boundary,
date disagreements, gaps and duplicate-date cases. Infer the year from anchored
chronology: late 2024 can legitimately use ESH25. Historical availability
remains unverified with every `available_at` null.

The separate [Verniman 2023 request](../requests/fulfilled/verniman_daily_levels__5.0.0.yaml)
collects January 1–December 31, 2023 under
`curated/external_levels/source=verniman/version=5.0.0/`, preserving all earlier
releases. It uses the same four canonical tables and viewing summary, with
all 365 calendar dates recorded in coverage. The December 29, 2023 seed reuses
the prior crawl's hash-pinned boundary capture and its original timestamps;
newly traversed posts receive new captures. The December 31 anchor keeps the
December 30–31 weekend in scope. Retain the source captures, chronological
ledger, public-feed comparison, older boundary, gaps and duplicate-date cases.
Infer the year from chronological month/day values; ESH24 can be legitimate
in late 2023. Source timestamp claims remain separate from capture time, and
every `available_at` remains null with historical availability unverified.

The separate [Verniman 2022 request](../requests/fulfilled/verniman_daily_levels__6.0.0.yaml)
collects January 1–December 31, 2022 under
`curated/external_levels/source=verniman/version=6.0.0/`, preserving all earlier
releases. It uses the same four canonical tables and viewing summary, with
all 365 calendar dates recorded in coverage. The December 30, 2022 seed reuses
the prior crawl's hash-pinned boundary capture and its original timestamps;
newly traversed posts receive new captures. The December 31 anchor keeps that
weekend date in scope. Retain source captures, the chronological ledger,
public-feed comparison, older boundary, gaps and duplicate-date cases. Infer
the year from chronological month/day values; ESH23 can be legitimate in late
2022. Source updated metadata alone cannot assign a body to 2022. Timestamp
claims remain separate from capture time, and every `available_at` remains null
with historical availability unverified. The observed older-link discontinuity
from May 2022 to an explicit December 2021 body is qualified in a separate
reviewed collection record; keep the original crawl ledger and log absent
2022 dates rather than assigning the older sequence to 2022.

The separate [Verniman 2021 request](../requests/fulfilled/verniman_daily_levels__7.0.0.yaml)
collects January 1–December 31, 2021 under
`curated/external_levels/source=verniman/version=7.0.0/`, preserving all earlier
releases. It retains the same four canonical tables and viewing summary, with
all 365 dates in coverage. The seed explicitly describes the final 2021 trading
session. Selected prior context captures retain their original timestamps;
their dates follow a new traversal anchored to December 31, 2021 rather than
the prior generic crawler's year assignments. Keep the original navigation
ledger, public-feed comparison, older boundary, gaps and duplicate-date cases.
Any feed-discovered detached plan requires supplemental source captures and
an explicit date review; its current navigation and distinct assignment method
remain recorded. Supplementary raw records preserve linked chart images with
extensionless or legacy-host URLs missed by the frozen capture helper. Keep
those image manifests and the reviewed collection alongside the original raw
captures. Source publication/update claims never establish pre-open availability:
every `available_at` remains null with historical availability unverified.

The separate [Verniman 2020 request](../requests/fulfilled/verniman_daily_levels__8.0.0.yaml)
collects January 1–December 31, 2020 under
`curated/external_levels/source=verniman/version=8.0.0/`, preserving all earlier
releases. It retains the same four canonical tables and viewing summary, with
all 366 calendar dates in coverage. The seed is the hash-pinned prior boundary
explicitly describing the final 2020 trading session; it retains its original
capture timestamps. Newly traversed posts receive fresh captures. Keep the
navigation ledger, fresh public-feed comparison, older 2019 boundary, gaps,
duplicate-date groups and extraction issues. Pandemic-era bodies carrying
May 2021 batch-update claims can still describe 2020 plans: use anchored
month/day chronology and source context, retaining metadata disagreements.
Any detached candidate requires a separate review and source captures.
Retain supplemental full-size image captures alongside the original crawl.
Publication/update claims and capture timestamps remain separate, and every
`available_at` remains null with historical availability unverified.

The 2020 schema additionally preserves original Plan A/B text and source
letters. Those letters can describe either direction in this year: stored
`side` follows consistent explicit above/buy or below/sell wording. Use
`levels.source_plan_branch` for the source letter and the outlook/summary
branch-identity fields for inspection. Earlier release schemas remain frozen.
Contradictory or duplicated directional assignments stay in source text/issues
without guessed numeric extraction.

The separate [Verniman 2019 request](../requests/fulfilled/verniman_daily_levels__9.0.0.yaml)
collects January 1–December 31, 2019 under
`curated/external_levels/source=verniman/version=9.0.0/`, preserving all earlier
releases. Keep the same four canonical tables, viewing summary, original A/B
text and source-letter fields, and all 365 calendar dates in coverage. The
hash-pinned prior boundary describing the final 2019 trading session retains
its original capture timestamps; newly traversed posts receive fresh captures.
Retain the navigation ledger, independent public-feed comparison, older 2018
boundary, gaps, duplicate-date groups and extraction issues. Record discovery
exhaustion and retrieval qualifications explicitly. Session years follow
anchored body chronology and retained source context; publication/update
metadata alone does not assign them. Economic side follows consistent explicit
instructions while the original A/B letter remains separate. Keep source
timestamp claims separate from capture times and preserve null `available_at`
with historical availability unverified.
In 9.0.0, an exact single numeric threshold can have `source_label = null`
when the source gives a price without a name. Its original text and an
`unlabelled_trigger_price` issue remain retained. Only explicit single trigger
points qualify; targets require labels, and ambiguous bare ranges/lists do not
produce numeric rows. Earlier release schemas and policies remain unchanged.

The separate [Verniman 2018 request](../requests/fulfilled/verniman_daily_levels__10.0.0.yaml)
collects January 1–December 31, 2018 under
`curated/external_levels/source=verniman/version=10.0.0/`, preserving all earlier
releases. Keep the same four canonical tables and viewing summary, original
A/B/C text and source letters, and bounded null-label trigger-point policy.
This release adds nullable `source_plan_c_text` and qualifies unresolved generic
ES delivery contracts with null plus a required issue. Literal single-digit
contract codes remain unchanged. Bounded below/bearish-internals “lean on”
scenarios retain their source wording and warning; the conditional trigger
stays distinct from the ancillary lean reference. Neutral or ambiguous
scenarios retain source text and issues without invented numeric assignments.
Coverage records every one of the 365 calendar dates, including gaps and
duplicate-date cases. The retained December 31 seed keeps its original
timestamps; its 2018 assignment follows the prior anchored chronology and
New Year context. Newly visited posts receive fresh source captures. Preserve
the navigation ledger, independent feed reconciliation, older 2017 boundary,
extraction issues and explicit discovery exhaustion or retrieval limitations.
Session years follow body chronology and corroborating source context rather
than publication/update metadata alone. Source timestamp claims remain
separate from capture time, and `available_at` remains null with historical
availability unverified.

The separate [Verniman 2017 request](../requests/fulfilled/verniman_daily_levels__11.0.0.yaml)
saves the currently retrievable 2017 plans under
`curated/external_levels/source=verniman/version=11.0.0/`, preserving earlier
releases and the same four canonical tables and summary. Of 40 daily plans,
28 state body dates; 12 retain null session dates and no numeric extraction.
Original source text, A/B/C labels, contracts, timestamp claims and capture
hashes remain available. Do not assign missing dates from metadata, image
names, permalinks or neighboring sessions.

The full 365-date ledger distinguishes observed dated posts from absence.
Navigation and a complete independent feed exhaust without a dated 2016
boundary; the original lower-boundary flag remains false. Retain pinned
completion evidence and all linked educational context, classified separately
from daily plans. January–October absence and unresolved dates are limitations
of the currently retained source, not proof of historical absence. Historical
availability remains unverified with every `available_at` null.

The separate [Verniman 2016 request](../requests/fulfilled/verniman_daily_levels__12.0.0.yaml)
recovers archived source revisions into
`curated/external_levels/source=verniman/version=12.0.0/`. Archived HTML and
historical feed responses belong under `raw/blogspot/verniman/archive_html/`;
archive indexes and discovery responses belong under `archive_discovery/`.
Keep failed attempts and image qualifications alongside successful captures.
Current blog resources at old permalink URLs do not replace historical bodies.

The same four canonical tables and viewing summary preserve explicit source
dates, unlettered plan prose, directional targets and exact prices. Actual source
letters stay null when absent. A `targets_only` side has no inferred trigger;
trigger interpretation distinguishes conditional, execution and failure
references. Source title dates, archive observation times, source publication
claims and present capture clocks remain distinct. Full 366-date coverage
describes observed retrieval; it does not prove every historical post survives.
Historical availability remains unverified and all earlier releases stay frozen.

### `features/`

Indicator-enriched data derived from a pinned curated dataset. Indicator definitions and versions live in `../catalog/indicators/`; values should be partitioned independently from the base bars:

```text
features/bars/<interval>/feature_set=<name>/version=<version>/product=<root>/year=<YYYY>/part-*.parquet
```

The `dridr_ohlcv_5m` feature-set identity is a base-data delivery rather than
an indicator set. It contains only request-specific five-minute OHLCV and
lineage derived from the pinned Phase 2 adjusted series:

```text
features/bars/5m/feature_set=dridr_ohlcv_5m/version=1.0.0/product=<ES|GC|NQ>/year=<YYYY>/part-000.parquet
```

Its manifest is `../catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json`.
Downstream DR/IDR features, labels, outcomes, statistics, and Pine payloads are
intentionally outside this dataset.

The `tradingview_daily_context` release preserves nine external one-day chart
exports (ES, NQ, GC, SI, CL, XAUUSD, VIX, VXN, GVZ). Exact source CSVs live in
`raw/tradingview/chart_exports/1d/20260924-8722875f919f/`; one confirmed-bar
Parquet file per asset lives in
`features/bars/1d/feature_set=tradingview_daily_context/version=1.0.0/asset=<asset>/`.
No year partition is needed for these small asset files. The source indicators
are retained with their exported close-based `available_at` timing; unfinished
bars are raw-only. See the [daily-context guide](../docs/daily-context-20260924.md),
[catalog manifest](../catalog/datasets/tradingview_daily_context__1.0.0.json),
and [quality record](../reports/quality/tradingview_daily_context__1.0.0.md).

The published `session_anchored_vwap` release is:

```text
features/bars/<2m|5m>/feature_set=session_anchored_vwap/version=1.0.0/product=<ES|NQ|GC>/year=<YYYY>/part-000.parquet
features/audits/feature_set=session_anchored_vwap/version=1.0.0/product_day_eligibility.parquet
```

It contains one wide row per eligible product/output bar. Both intervals use
the same whole-product-day audit; all bars are independently aggregated from
the pinned one-minute source. Eligibility is retrospective research sample
selection, not a live feature. Missing expected minutes are never filled, and
the audit does not equate an absent no-trade minute with confirmed corruption.
See `../catalog/datasets/session_anchored_vwap__1.0.0.release.json` and
`../reports/quality/session_anchored_vwap__1.0.0.md`.

### `range_xv/`

The Sahadeva data tree contains historical ATAS exports. The fourteen enhanced
CSV files were corrected in place on 2026-09-24 to express derived timestamps
in New York wall time. Original ATAS timestamp strings and OHLC values remain
in the same rows. The [Range XV guide](range_xv/README.md) explains the clock
assumption, and the [migration record](../docs/migration/range-xv-clock-normalization-20260924.json)
maps old and current hashes. Historical studies may refer to short-window
exports absent from the longer source tree; do not silently substitute a newer
export. Compatibility CSV links under `legacy/sahadeva/data/` resolve here.

The newer, longer ATAS export set is stored separately under
`range_xv/20191101_20260924/`: `source/` retains the downloaded five-column CSV
bytes under consistent product/setting/date names, `enhanced/` provides the
existing Range XV research column layout, and `range_xv_exports_manifest.json`
pins both forms by hash. New Range XV research can pin this longer snapshot
after reviewing its chart-specific gaps, especially in GC. The older top-level
files and manifest now carry the corrected clock. Completed historical runs
retain their original input hashes and are not rewritten.
The longer set adds ES 4 RXV but does not include GC 20 RXV; do not silently mix
the older GC 20 file into a new common-history study. See the
[long-history import and gap audit](../docs/range-xv-long-history-20260924.md).

The [October 1 currency-futures snapshot](../docs/range-xv-fx-20261001.md) lives
separately at `range_xv/fx_20170721_20261001/`. It adds 6E, 6B, 6J, and 6S,
each at filename-labelled 4- and 5-tick settings: 2,002,278 OHLC rows over
2,377 common inferred sessions. Raw exports, eleven-column enhanced CSVs,
row-quality flags, session profiles, and conversion provenance are retained.
No volume was exported. Derived times use the same inferred New York clock
conversion; the final session is partial. Pin the new
[tracked manifest](../docs/data/range_xv_fx_20170721_20261001.json) for new work.
The older exports, hash-pinned Range XV README, manifests, and legacy links
remain unchanged. Conversion belongs to Bhishma; these retained ATAS inputs
remain in Sahadeva's existing Range XV storage.

### `research/sahadeva/`

This is the complete copied original Sahadeva `work/` tree, preserving its
study/run directories and event-level files. It is retained research evidence,
not disposable scratch or a cache. `legacy/sahadeva/work` resolves here.
Keep its provenance and backups. New scratch or staged executions belong in
the workspace's [work directory](../work/README.md), with completed evidence
sealed according to the [run guide](../runs/README.md).

## Supporting directories

- `inbox/databento/` is a temporary landing zone for newly downloaded vendor archives. After validation, deliveries move into their batch-specific `raw/` directory; the inbox is not a permanent data layer.
- `../catalog/datasets/` records input batches, transformation versions, schemas, row counts, and output checksums.
- `../catalog/schemas/` defines the contracts consumed by downstream repositories.
- `../catalog/indicators/` defines formulas, parameters, warm-up rules, and feature versions.
- `../reports/quality/` stores human-readable profiles and validation results.
- `../packages/bhishma/src/abacus_bhishma/` contains ingestion, validation, transformation, and indicator pipelines.
- `../packages/bhishma/tests/` protects those pipelines and schema contracts.

## Why the product and instrument-type partitions matter

The current Databento request used the parent symbols `ES.FUT`, `NQ.FUT`, and `GC.FUT`. Its DBN stream includes many individual contracts and exchange-listed spread instruments; it is not a set of three prebuilt continuous series. Keeping `product`, `instrument_type`, and continuous-series rules explicit prevents spread prices, reused contract symbols, or hidden rollover choices from leaking into strategy research.

## Verify the relocated files

From the workspace root, run the read-only destination check:

```sh
python3 scripts/verify-storage.py
```

It verifies the recorded relocated-file hashes without needing either original
project folder. The [relocation record](../docs/migration/storage-relocation-20260922.md)
describes the inventory and optional source comparison. Storage verification
does not rebuild data, rerun research, or validate strategy conclusions.

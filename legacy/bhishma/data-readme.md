# Data layout

The data tree separates vendor source material from rebuildable intermediate files and published research datasets.

## Layers

### `raw/`

Immutable files exactly as delivered by a provider, including manifests, checksums, query metadata, and condition reports. A vendor batch uses this path:

```text
raw/<provider>/<dataset>/<schema>/<batch-id>/
```

Never edit a file in place under `raw/`. If a vendor issues a correction, archive it as a new batch.

The current Databento definition batch preserves the original ZIP, its three support JSON files, and all 5,100 daily compressed DBN files together under its provider job ID. The `.dbn.zst` files remain compressed because the Databento reader can stream them directly; decoded or filtered derivatives belong in `staging/` or `curated/`, not beside the vendor payload.

### `staging/`

Lossless decoded or extracted forms of raw files. Staging exists to make inspection and downstream conversion easier, but every file here must be reproducible from a raw batch.

The current `.dbn` file is the direct Zstandard decompression of its `.dbn.zst` source; no rows or metadata were transformed.

### `curated/`

Validated, symbol-mapped, analysis-ready datasets with stable schemas. Curated data has three distinct products:

- `instruments/` contains contract and symbology reference data.
- `bars/` contains contract-level bars and keeps outrights separate from spreads.
- `continuous/` contains explicitly constructed continuous futures series.

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

## Supporting directories

- `inbox/databento/` is a temporary landing zone for newly downloaded vendor archives. After validation, deliveries move into their batch-specific `raw/` directory; the inbox is not a permanent data layer.
- `../catalog/datasets/` records input batches, transformation versions, schemas, row counts, and output checksums.
- `../catalog/schemas/` defines the contracts consumed by downstream repositories.
- `../catalog/indicators/` defines formulas, parameters, warm-up rules, and feature versions.
- `../reports/quality/` stores human-readable profiles and validation results.
- `../src/` contains ingestion, validation, transformation, and indicator pipelines.
- `../tests/` protects those pipelines and schema contracts.

## Why the product and instrument-type partitions matter

The current Databento request used the parent symbols `ES.FUT`, `NQ.FUT`, and `GC.FUT`. Its DBN stream includes many individual contracts and exchange-listed spread instruments; it is not a set of three prebuilt continuous series. Keeping `product`, `instrument_type`, and continuous-series rules explicit prevents spread prices, reused contract symbols, or hidden rollover choices from leaking into strategy research.

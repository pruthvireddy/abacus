# Abacus Bhishma

Abacus Bhishma is a historical market data repository for research, feature engineering, and reproducible strategy development.

The repository's job is to preserve trusted source data, document its provenance, and incrementally produce analysis-ready datasets with well-defined indicators. Trading strategies and execution systems belong in downstream repositories; they should consume versioned outputs from this project rather than each implementing their own data-cleaning pipeline.

## Current dataset

The repository currently contains three CME futures families. The available market-data aggregation is **one-minute OHLCV**; daily, tick, and other bar intervals have not been added. A separate point-in-time `definition` dataset supplies contract reference data such as symbols, expirations, tick sizes, and instrument types.

### Available assets

| Parent symbol | Asset | Bar aggregation | Observed bar coverage (UTC) | Bar days | Bars | Observed symbols (outright / spread) |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `ES.FUT` | E-mini S&P 500 futures | 1-minute OHLCV | 2010-06-06 – 2026-09-18 | 5,054 | 8,696,827 | 40 / 151 |
| `NQ.FUT` | E-mini Nasdaq-100 futures | 1-minute OHLCV | 2010-06-06 – 2026-09-18 | 5,054 | 7,316,559 | 40 / 119 |
| `GC.FUT` | Gold futures | 1-minute OHLCV | 2010-06-06 – 2026-09-18 | 5,056 | 15,774,757 | 120 / 1,317 |

“Days available” counts distinct **UTC calendar dates containing at least one record** for that asset family. It is not a count of weekdays or exchange-defined trading sessions. Coverage begins at `2010-06-06 22:00:00 UTC`; the last observed bar for all three families is `2026-09-18 20:59:00 UTC`.

The symbol counts describe raw contract codes observed in the data. Contract codes can be reused across decades, while the DBN metadata supplies dated mappings to the corresponding instrument IDs. Spread counts include exchange-listed spread instruments returned by each parent-symbol query.

### Instrument definitions

| Property | Value |
| --- | --- |
| Provider batch | `GLBX-20260920-QQQSGCKWES` |
| Dataset and schema | CME Globex MDP 3.0 (`GLBX.MDP3`), `definition` |
| Parent products | `ES.FUT`, `NQ.FUT`, `GC.FUT` |
| Requested range | 2010-06-06 through 2026-09-19 |
| Delivered coverage | 2010-06-06 through 2026-09-18 |
| Daily definition files | 5,100 compressed DBN files |
| Encoding and compression | Databento Binary Encoding (`DBN`), Zstandard (`zstd`) |
| Compressed definition payload | 81,288,444 bytes (77.5 MiB) |
| Original download ZIP | 85,380,559 bytes (81.4 MiB) |

Definitions are point-in-time reference records, not price bars and not a prebuilt continuous series. The parent-symbol request includes outright contracts and exchange-listed spreads. The raw daily files will be filtered to the instrument IDs selected by the continuous roll map when the curated contract guide is built.

| Property | Value |
| --- | --- |
| Provider | Databento |
| Dataset | CME Globex MDP 3.0 (`GLBX.MDP3`) |
| Schema | One-minute OHLCV (`ohlcv-1m`) |
| Requested range | 2010-06-06 through 2026-09-19 |
| Input symbology | Parent futures symbols |
| Output symbology | Instrument ID |
| Encoding | Databento Binary Encoding (`DBN`) |
| Compression | Zstandard (`zstd`) |
| Records | 31,788,143 one-minute bars |
| Compressed size | 386,880,800 bytes (369 MiB) |
| Decompressed size | 1,783,295,480 bytes (1.66 GiB) |

The query's end timestamp is `2026-09-20 00:00:00 UTC` and is exclusive, so its requested calendar window runs through 2026-09-19. The last bar actually present is timestamped `2026-09-18 20:59:00 UTC`. The provider metadata and manifest are the authoritative record of the request and delivered files.

The parent-symbol query returns an instrument-level dataset, not three continuous futures series. The current batch contains outright contracts as well as exchange-listed spreads. Continuous ES, NQ, and GC series will therefore be explicit derived products with documented roll and adjustment rules.

## Published continuous datasets

Phase 1 is published as `volume_lead_unadjusted_v1`. It uses Databento's volume-ranked `ES.v.0`, `NQ.v.0`, and `GC.v.0` mappings, switches only at Globex session boundaries, and preserves the selected outright contract's source OHLCV values exactly.

| Product | Aggregation | Coverage (UTC) | Rows | Mapping intervals | Rolls | First / last contract |
| --- | --- | --- | ---: | ---: | ---: | --- |
| ES | 1-minute OHLCV | 2010-06-06 22:00 – 2026-09-18 20:59 | 5,694,142 | 67 | 66 | `ESM0` / `ESZ6` |
| NQ | 1-minute OHLCV | 2010-06-06 22:00 – 2026-09-18 20:59 | 5,520,074 | 67 | 66 | `NQM0` / `NQZ6` |
| GC | 1-minute OHLCV | 2010-06-06 22:00 – 2026-09-18 20:59 | 5,651,836 | 82 | 81 | `GCQ0` / `GCZ6` |

The canonical prices are signed 64-bit fixed-point integers with scale `1e-9`; volume is unchanged. Timestamps are UTC nanoseconds and each row also carries its `America/New_York` Globex `session_date`, raw contract symbol, date-scoped instrument ID, mapping interval, and roll marker.

Phase 2 is published as `volume_lead_back_adjusted_v1`. It retains every Phase 1 row and adds a constant `price_adjustment` per mapping interval to OHLC only. Each roll gap is the incoming contract's prior-session close minus the outgoing contract's close from the same session. Adjustments accumulate backward, leaving the latest contract at its actual price. Volume and every identifier remain unchanged.

The five data concepts are deliberately separate:

- **Parent-symbol raw data** is the immutable vendor delivery for `ES.FUT`, `NQ.FUT`, and `GC.FUT`; it contains many outright contracts and exchange-listed spreads.
- **Individual outright contracts** are identified from point-in-time definitions, not symbol punctuation.
- **The Phase 1 unadjusted continuous series** selects one volume-leading outright per session. Its values are real traded-contract values, so the price level can jump at rolls. This makes it appropriate for execution/P&L modeling and the auditable input to adjustment.
- **The Phase 2 back-adjusted series** removes contract-price discontinuities using exact additive adjustments. It is a synthetic analytical series for charts, indicators, features, and signals—not execution or P&L prices.
- **Future feature datasets** will derive indicators from a pinned Phase 2 manifest without changing either continuous base layer.

Build or validate entirely offline:

```bash
./scripts/build-continuous-phase1
./scripts/validate-continuous-phase1
./scripts/build-continuous-phase2
./scripts/validate-continuous-phase2
```

Existing completed outputs are protected; rebuilding either phase requires the corresponding build command with `--force`. See the Phase 1 [manifest](catalog/datasets/volume_lead_unadjusted_v1.json) and [quality report](reports/quality/volume_lead_unadjusted_v1.md), and the Phase 2 [manifest](catalog/datasets/volume_lead_back_adjusted_v1.json) and [quality report](reports/quality/volume_lead_back_adjusted_v1.md).

Load either variant without changing the downstream schema-selection code:

```python
from pathlib import Path
from abacus_bhishma.continuous_loader import open_continuous_dataset, price_to_float

root = Path("/Users/ppanati/Documents/projects/abacus-bhishma")
es = open_continuous_dataset(root, "ES", variant="back_adjusted")
sample = es.head(1_000, columns=["ts_event", "close", "price_adjustment"])
display_close = price_to_float(sample["close"].to_numpy())
```

## Published session-anchored VWAP features

`session_anchored_vwap` version `1.0.0` publishes independently aggregated
2-minute and 5-minute ES, NQ, and GC bars with Globex, Asia, London, and NY
anchored HLC3 VWAPs, population sigma bands, distances, session membership,
and descriptive completed-bar events. Both intervals use the same strict,
retrospectively selected product-day population.

| Dataset ID | Interval | ES rows/days | NQ rows/days | GC rows/days |
|---|---:|---:|---:|---:|
| `session_anchored_vwap_2m_v1` | 2m | 715,530 / 1,037 | 812,130 / 1,177 | 569,250 / 825 |
| `session_anchored_vwap_5m_v1` | 5m | 286,212 / 1,037 | 324,852 / 1,177 | 227,700 / 825 |

The [release manifest](catalog/datasets/session_anchored_vwap__1.0.0.release.json)
links both interval manifests, the [eligibility audit](data/features/audits/feature_set=session_anchored_vwap/version=1.0.0/product_day_eligibility.parquet),
and the [quality report](reports/quality/session_anchored_vwap__1.0.0.md).
The audit covers the complete pinned source range, including unsupported
historical regimes and excluded days; no missing source minute is filled.

Load a pinned slice:

```python
from pathlib import Path
from abacus_bhishma.feature_loader import load_session_anchored_vwap

root = Path("/Users/ppanati/Documents/projects/abacus-bhishma")
features = load_session_anchored_vwap(
    root,
    "ES",
    "5m",
    version="1.0.0",
    start_date="2024-01-01",
    end_date="2024-02-01",
    columns=["ts_event", "available_at", "close", "globex_vwap", "ny_distance_ticks"],
)
```

Rebuild and validate (completed versions are overwrite-protected):

```bash
./scripts/build-session-anchored-vwap
./scripts/validate-session-anchored-vwap
```

## Repository layout

```text
.
├── catalog/
│   ├── datasets/                 # Versioned dataset manifests
│   ├── indicators/               # Indicator definitions and parameters
│   └── schemas/                  # Machine-readable schema contracts
├── data/
│   ├── raw/                      # Immutable vendor deliveries
│   │   └── databento/GLBX.MDP3/
│   │       ├── ohlcv-1m/<batch-id>/
│   │       ├── definition/<batch-id>/
│   │       └── symbology/continuous/volume-rank-0/
│   ├── staging/                  # Lossless, rebuildable decoded data
│   │   └── databento/GLBX.MDP3/ohlcv-1m/<batch-id>/*.dbn
│   ├── curated/                  # Validated research-ready datasets
│   │   ├── instruments/
│   │   ├── bars/1m/product=<root>/instrument_type=<type>/
│   │   └── continuous/1m/product=<root>/roll=<method>/variant=<variant>/
│   └── features/                 # Versioned indicator-enriched datasets
├── reports/quality/              # Data profiles and validation reports
├── src/
│   ├── ingest/
│   ├── indicators/
│   ├── transform/
│   └── validate/
└── tests/
```

See [`data/README.md`](data/README.md) for the data-layer and partitioning conventions. Batch profiles are available for the [one-minute bars](reports/quality/GLBX-20260920-577W4VCSK7.md) and [instrument definitions](reports/quality/GLBX-20260920-QQQSGCKWES.md).

## Requesting derived datasets

Other repositories can request session-aware higher-timeframe bars and reusable indicator columns with the [feature-dataset request template](requests/templates/feature-dataset-request.yaml). Copy and complete the template rather than editing it in place, then bring the filled request back to this repository. See [requests/README.md](requests/README.md) for the ownership and delivery conventions.

Published request-specific deliveries:

| Dataset ID | Timeframe | Products | Version | Manifest | Quality report |
|---|---|---|---|---|---|
| `tv_indicators__dridr_ohlcv_5m__v1` | 5 minutes | ES, GC, NQ | `1.0.0` | [manifest](catalog/datasets/tv_indicators__dridr_ohlcv_5m__v1.json) | [report](reports/quality/tv_indicators__dridr_ohlcv_5m__v1.md) |
| `session_anchored_vwap_2m_v1` | 2 minutes | ES, GC, NQ | `1.0.0` | [manifest](catalog/datasets/session_anchored_vwap_2m_v1.json) | [report](reports/quality/session_anchored_vwap__1.0.0.md) |
| `session_anchored_vwap_5m_v1` | 5 minutes | ES, GC, NQ | `1.0.0` | [manifest](catalog/datasets/session_anchored_vwap_5m_v1.json) | [report](reports/quality/session_anchored_vwap__1.0.0.md) |

## Databento API access

Project utilities authenticate with a dedicated API key stored in macOS Keychain. The secret is never stored in this repository, passed on the command line, or printed by the utilities. The Keychain service name is `abacus-bhishma.databento`.

Create the isolated Python environment once:

```bash
./scripts/bootstrap
```

Available commands:

```bash
# Securely create or rotate the Keychain entry using a hidden prompt
./scripts/databento setup-key

# Make a read-only authentication check
./scripts/databento check

# Fetch the free ES/NQ/GC volume-ranked continuous mappings
./scripts/databento fetch-roll-map

# Estimate definition-data cost without submitting a download
./scripts/databento estimate-definitions

# Download definitions only when the estimate is within an explicit cost cap
./scripts/databento download-definitions --max-cost-usd 0.02
```

The mapping command requests `ES.v.0`, `NQ.v.0`, and `GC.v.0` from Databento's free symbology-resolution endpoint and writes the dated response under:

```text
data/raw/databento/GLBX.MDP3/symbology/continuous/volume-rank-0/
```

The current mapping resolves successfully across the full requested range and contains 67 ES intervals, 67 NQ intervals, and 82 GC intervals. These intervals will drive contract selection before price back-adjustment.

The archived definition batch was acquired through Databento's portal as a parent-symbol request and is stored under:

```text
data/raw/databento/GLBX.MDP3/definition/GLBX-20260920-QQQSGCKWES/
```

Billable downloads require an explicit maximum cost. The command obtains a fresh estimate and aborts before requesting data if the estimate exceeds that limit. Keep a historical monthly usage limit enabled in the Databento portal.

## Purpose and scope

This repository is intended to become the shared data foundation for quantitative research across other projects. Its scope includes:

- preserving raw vendor data and its provenance;
- validating integrity, schema, timestamps, and market coverage;
- normalizing data into stable, efficient research formats;
- handling futures-specific concerns such as contracts, expiries, and roll rules explicitly;
- enriching bars with documented, reproducible indicators and features;
- versioning datasets so experiments can be reproduced; and
- publishing clear interfaces for downstream backtests and strategies.

It is intentionally **not** the home for strategy logic, portfolio construction, order execution, broker integrations, or live trading infrastructure. Those systems should treat this repository's curated datasets as inputs.

## Data lifecycle

Data should move through a small number of clearly separated stages:

```text
Raw vendor batch  ->  Staging decode  ->  Curated bars  ->  Enriched features
    immutable          rebuildable        validated          versioned
```

Raw downloads should remain immutable. Corrections, transformations, continuous-contract construction, and indicator calculations should create new versioned artifacts rather than altering the source files. Every derived dataset should be traceable to:

1. its source batch and checksum;
2. the code and configuration that produced it;
3. its contract and session conventions;
4. its indicator definitions and parameters; and
5. the version of the resulting schema.

## Guiding conventions

- **UTC by default.** Store timestamps in UTC and document any exchange-session interpretation separately.
- **No hidden roll logic.** Raw instrument-level records, continuous series, and back-adjusted series are distinct products and must be labeled as such.
- **No look-ahead leakage.** Features must use only information available at their recorded timestamp.
- **Deterministic outputs.** Given the same source batch and configuration, a transformation should produce the same result.
- **Quality before enrichment.** Validate ordering, duplicates, gaps, price/volume ranges, and session boundaries before computing indicators.
- **Stable contracts for consumers.** Schema changes and indicator-definition changes should be versioned rather than silently applied.

## Planned evolution

Near-term additions are expected to include:

- scripts for decoding DBN and producing analysis-friendly partitions;
- integrity and coverage reports;
- canonical schemas for raw, normalized, and enriched bars;
- explicit futures contract and rollover metadata;
- a registry of indicators with formulas, parameters, warm-up periods, and versions; and
- examples showing downstream projects how to discover and load a pinned dataset version.

## Data handling notes

The market data files are large binary artifacts. The definition batch retains its original ZIP alongside the extracted compressed payload and vendor support files. Staging contains the losslessly decompressed OHLCV DBN file. If this directory is placed under Git version control, use an appropriate large-file or object-storage strategy rather than ordinary Git blobs. Staging data is reproducible from raw data and does not need to be retained in remote version history.

Market data access, use, and redistribution may be governed by Databento and exchange licensing terms. Treat the contents as licensed data and verify those terms before sharing or publishing any source or derived dataset.

## Status

Phases 1 and 2 are complete and validated. The repository publishes both the unadjusted contract-truth series and the backward-additively-adjusted analytical series for ES, NQ, and GC. Indicator enrichment remains future work.

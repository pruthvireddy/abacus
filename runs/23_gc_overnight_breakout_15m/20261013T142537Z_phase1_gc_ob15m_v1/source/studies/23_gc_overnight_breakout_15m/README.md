# GC- Overnight Breakout 15M

Study `23_gc_overnight_breakout_15m` · Phase 1 approved October 13, 2026 · Protocol `1.0.0`.

Phase 1 measures the fixed baseline overnight breakout, one executable GC contract per accepted broker day. The user authorized implementation, input preparation, execution, verification, saved evidence, publication and production deployment on the existing Narada website. Phase 2 midpoint/reclaim/interior entries, re-entry, additional trades and filters remain unimplemented and uncomputed.

Read the [frozen Phase 1 protocol](protocol-phase1.md), [settings](config-phase1.json), [input audit](phase1-input-audit.md) and [market lock](phase1-inputs.lock.json). The [research plan](plan.md) retains future Phase 2 proposals; its earlier documentation-only scope is superseded for Phase 1. Publishing annual baseline outcomes creates prior exposure for later research; those years cannot be called untouched Phase 2 holdouts.

The baseline uses fixed GMT+3, range [00:00,07:00), trading [07:00,20:00), boundary stop touches, OCA cancellation and one accepted trade per broker day. Regular 15-minute candles govern submission and stop updates; observed unadjusted one-minute candles resolve fills approximately. Initial 1% stops are boundary anchored; only a surviving entry candle resets from actual fill at its close. The evening close is queued for the next opening. Native standing-order semantics and the explicit causal quality overlay remain distinct from the indicator's missing-bar fallback.

Immutable `volume_lead_unadjusted_v1` version `1.0.0` supplies 3,046,589 source minutes across 45 contracts, from January 1, 2018 23:00 UTC through September 18, 2026 20:59 UTC (completion21:00). The 2026 year is partial. The frozen audit identifies994 causally eligible broker days and1,106 valid complete ranges. Missing range minutes, uncertified holiday candidates, roll barriers and the first loaded day reduce support. Later missing execution evidence censors accepted trades instead of excluding their signals. GC economics are0.1tick,100USD/point and whole contracts; the source account's10,000USD/1%risk/10xcap is a separate view.

Prespecified assumed costs are2.50USD/contract/side plus one adverse tick/fill, with zero-cost and0/1/2tick executions. These are scenarios, not the user's broker charges. Reporting uses actual estimated entry fill in America/New_York with approved Asia/London/New York/outside windows. Within-minute fill times retain bounds, and native TradingView compilation/replay remains unverified.

## Retained sources

- [Original strategy](sources/original-strategy.pine), by WillyAlgoTrader.
- [Indicator adaptation](sources/indicator-adaptation.pine).
- [Source differences](source-rules.md) and [source-byte lock](inputs.lock.json).
- [Screenshot](sources/indicator-chart-reference.png), appearance reference only; no market-data evidence or inferred meanings for unlabeled marks.

The midpoint is visual in the supplied scripts. Indicator H10 signal-close diagnostics are omitted from this Phase 1 execution and are distinct from trade results.

## Ownership and checks

Study implementation, aggregation, exporter and tests belong here. Bhishma owns immutable data and public loaders; Narada renders explicitly selected saved report cells. Stage new output under `work/23_gc_overnight_breakout_15m/<run-id>/`; seal only verified evidence under a unique `runs/23_gc_overnight_breakout_15m/<run-id>/`. Retain large event/input evidence under `data/research/sahadeva/` with hashes and locators. Preserve completed runs and all earlier publication routes. Follow the [study guide](../AGENTS.md), [architecture](../../ARCHITECTURE.md) and [evidence contract](../../docs/evidence-contract.md).

```sh
UV_CACHE_DIR=/private/tmp/abacus-study23-uv-cache ./scripts/check-workspace --check study-23
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 scripts/build-research-index.py --check
```

Numerical tests use the existing locked environment without sync. The broader default gate's missing raw roll-map and unavailable ES definition prerequisites are recorded separately; they do not establish failure of the selected GC release bytes or excuse required study verification. Run records will identify actual executed checks and their limits.

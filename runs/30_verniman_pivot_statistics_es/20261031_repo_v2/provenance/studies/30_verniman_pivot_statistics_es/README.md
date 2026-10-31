# Verniman Pivot Statistics — ES

Study `30_verniman_pivot_statistics_es` plans daily, section and event statistics
around Verniman's ES pivot using Globex VWAP, a five-minute EMA20/50 cloud and
three-minute EMA6. The requested calendar is 2020-01-01–2026-10-30 inclusive.

**Authorized scope: the full descriptive workflow using repository-retained
data and pivots only, through saved statistics and local Narada presentation.**
External acquisition is cancelled. Retained market data currently ends
2026-09-18; keep the later requested dates as explicit coverage gaps. Reuse
compatible prebuilt OHLCV wherever possible. Historical plan availability remains
unverified; trading-strategy execution and hosted deployment are separate work.

Read the [approved roadmap](plan.md), [protocol](protocol-1.0.0.md),
[statistics catalog](statistics.md), [settings](study.yaml),
[input declaration](inputs.lock.json), [decision record](notes.md), and
[verification record](verification.md). The protocol records approved future
measurements; it is not a receipt that those measurements have been executed.

## Phase 1 commands

From the workspace root, using the existing locked environment without sync:

```sh
./scripts/uv run --locked --no-sync python studies/30_verniman_pivot_statistics_es/run.py audit --run-id <unique-run-id>
./scripts/uv run --locked --no-sync python studies/30_verniman_pivot_statistics_es/run.py verify-audit --stage work/30_verniman_pivot_statistics_es/<unique-run-id>
```

The audit inventories retained sources and required data. It does not calculate
market outcomes or manufacture feature values. Later commands are recorded in
the execution verification record. Keep source-only inventory
counts separate from eligible research-day counts and scientific results.
The actual command/results and any missing prerequisites belong in the
[verification record](verification.md). Do not infer a completed audit from
the existence of these command examples.

The saved-chart integration check uses the existing Node 24 and Narada-installed
Sharp runtime when Matplotlib is absent. It rasterizes authored SVG from saved
summary cells only; it installs no packages and does not calculate statistics.
Its retained input/renderer receipt identifies source rows, hashes and versions.

## Measurement and ownership

The primary input is a single-price pivot with a resolved source date, source
interpretation and exact quoted ES delivery contract. A nominal 09:25 plan
time is distinct from a verified `available_at`. Preserve image/recollection
observations separately from captured canonical plans; do not fill gaps using
another contract, an unpriced chart position, a midpoint or a retrospective
price match.

Bhishma supplies pinned same-contract one-minute OHLCV and reusable features.
Sahadeva supplies study-specific audit decisions, events, outcomes and saved
statistics. Narada will present explicit selected bundles after the research
and presentation phases are approved. Full ledgers remain retained evidence.

The study's three RTH sections are Opening range 09:30–10:30, New York AM
10:30–12:30 and New York PM 12:30–16:00, all America/New_York. Price and EMA6
crossings use completed three-minute closes; the cloud always uses five-minute
bars. This study does not substitute Study 28's interval-specific VWAP or Study
29's reconstructed indicator for the requested pivot and feature definitions.

Stage new output under `work/30_verniman_pivot_statistics_es/`. Follow the
[study guide](../AGENTS.md), [run lifecycle](../../runs/README.md) and
[architecture](../../ARCHITECTURE.md) before extending scope.

## Repository-only execution

The input delivery is already published; never rebuild that version. New outcome
runs use a fresh run ID and the pinned existing inputs. After a successful freeze,
use `run.py execute`, `run.py render` and `run.py verify`, each with an explicit
`--stage` path. Prepare the six sources with `publish_web.py <stage> --run-id <id>`
before verification/sealing. `run.py seal` refuses failed or stale evidence.

The owning gate is `./scripts/check-workspace --check study-30`. Its synthetic
presentation fixture uses Node24 and the existing independent Narada installation
for static PNG rendering; it does not install dependencies, rebuild the website
or read retained market data. See [verification](verification.md) for actual
checks and [Phase1/input audit](phase1-audit.md) for source and feature coverage.

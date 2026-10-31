# Verniman Pivot Statistics — ES

Study `30_verniman_pivot_statistics_es` measures daily, section and event statistics
around Verniman's ES pivot using Globex VWAP, a five-minute EMA20/50 cloud and
three-minute EMA6. The requested calendar is 2020-01-01–2026-10-30 inclusive.

**Completed: all 20 ranked statistics and two local Narada priority reports.**
The selected [ranked report](../../runs/30_verniman_pivot_statistics_es/20261031_ranked_v2/ranked-report.md)
retains 875 pivot-matched RTH, 1,308 VWAP-only RTH and 1,292 full-Globex sessions,
each spanning 2020-01-03–2026-09-18. Retained market sessions begin 2020-01-01;
the requested calendar still ends October 30. Cohorts, zero-cross days, missing
support and actual period bounds remain explicit. Historical pivot availability
is unverified; fills, costs and profitability are untested.

Open [Narada Explore](http://127.0.0.1:4173/studies/verniman-pivot-statistics-es/explore/)
while the local preview runs. **Pivot statistics** and **Globex VWAP statistics**
present the ranked questions with typed saved filters, four selected charts each,
summary CSVs and eligible-period bounds. The six original views remain under
**Original baseline**, attributed to `20261031_repo_v2` with its separate
operational correction unchanged. The [implementation matrix](implementation-matrix.md)
and [verification record](verification.md) describe completed coverage and limits.

Read the [approved roadmap](plan.md), [ranked protocol](protocol-2.0.0.md),
[original protocol](protocol-1.0.0.md),
[statistics catalog](statistics.md), [settings](study.yaml),
[input declaration](inputs.lock.json), [decision record](notes.md), and
[verification record](verification.md). Definitions and executed evidence are
separate records; the selected frozen run and its receipts identify actual checks.

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
statistics. Narada presents explicitly selected saved bundles. Full ledgers
remain retained private evidence, with hashes and locators in the selected run.

The study's three RTH sections are Opening range 09:30–10:30, New York AM
10:30–12:30 and New York PM 12:30–16:00, all America/New_York. Price and EMA6
crossings use completed three-minute closes; the cloud always uses five-minute
bars. This study does not substitute Study 28's interval-specific VWAP or Study
29's reconstructed indicator for the requested pivot and feature definitions.

Stage new output under `work/30_verniman_pivot_statistics_es/`. Follow the
[study guide](../AGENTS.md), [run lifecycle](../../runs/README.md) and
[architecture](../../ARCHITECTURE.md) before extending scope.

## Repository-only execution

The [ranked extension protocol](protocol-2.0.0.md) and
[20-statistic matrix](implementation-matrix.md) add actual VWAP crossings,
EMA-reference recrosses and paired-line paths. Use the separate `ranked.py`
lifecycle for this extension: `freeze --run-id <fresh-id>`, then `audit`,
`execute`, `render`, `parity`, `verify`, `publish` and `seal`, each with the
explicit `--stage` path. Required local Narada checks precede sealing. The
original six reports remain attributed to their original frozen run.

For the original baseline lifecycle, the input delivery is already published;
never rebuild that version. New outcome
runs use a fresh run ID and the pinned existing inputs. After a successful freeze,
use `run.py execute`, `run.py render` and `run.py verify`, each with an explicit
`--stage` path. Prepare the six sources with `publish_web.py <stage> --run-id <id>`
before verification/sealing. `run.py seal` refuses failed or stale evidence.

The owning gate is `./scripts/check-workspace --check study-30`. Its synthetic
presentation fixture uses Node24 and the existing independent Narada installation
for static PNG rendering; it does not install dependencies, rebuild the website
or read retained market data. See [verification](verification.md) for actual
checks and [Phase1/input audit](phase1-audit.md) for source and feature coverage.

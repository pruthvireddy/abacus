# Verniman Pivot Statistics — ES

Study `30_verniman_pivot_statistics_es` measures daily, section and event statistics
around Verniman's ES pivot using Globex VWAP, a five-minute EMA20/50 cloud and
three-minute EMA6. The requested calendar is 2020-01-01–2026-10-30 inclusive.

**Current notebook edition: six themes and 21 descriptive insights.**
The study-local [notebook](vern-pivot-cross-statistics.ipynb) owns its analytical
code, narrative, findings and chart/table output. Its selected executed content
is rendered in Narada's Research paper design without Python source.
The [V2 notebook run](../../runs/30_verniman_pivot_statistics_es/20261108T040901Z_notebook_themes_v2/report.md)
records its execution, exact saved-result comparisons and publication checks.
The earlier ranked evidence remains retained:
The selected [ranked report](../../runs/30_verniman_pivot_statistics_es/20261031_ranked_v2/ranked-report.md)
retains 875 pivot-matched RTH, 1,308 VWAP-only RTH and 1,292 full-Globex sessions,
each spanning 2020-01-03–2026-09-18. Retained market sessions begin 2020-01-01;
the requested calendar still ends October 30. Cohorts, zero-cross days, missing
support and actual period bounds remain explicit. Historical pivot availability
is unverified; fills, costs and profitability are untested.

Open [Narada Results](http://127.0.0.1:4173/studies/verniman-pivot-statistics-es/)
while the local preview runs. Results contains **Opening context**, **Crossing
activity**, **Breaks & confirmation**, **After the cross**, **VWAP & cloud** and
**Timing & stability** as switchable theme tabs. Only the active theme's insights
are shown. Compact scope/source disclosures retain
the separate VWAP-only companions, ranked reports and six original baseline views
with their original source runs. The notebook and published evidence are unchanged.
The [implementation matrix](implementation-matrix.md) and
[verification record](verification.md) describe evidence coverage and limits.

Read the [approved roadmap](plan.md), [ranked protocol](protocol-2.0.0.md),
[original protocol](protocol-1.0.0.md),
[statistics catalog](statistics.md), [settings](study.yaml),
[input declaration](inputs.lock.json), [decision record](notes.md), and
[verification record](verification.md). Definitions and executed evidence are
separate records; the selected frozen run and its receipts identify actual checks.

## Insight notebook and Narada presentation

The editable [V2 notebook](vern-pivot-cross-statistics.ipynb) has 119 ordinary
cells, including 68 visible Python cells, grouped into six themes. Its 21 insights
cover all 20 primary ranked pivot question families plus the reviewed annual
frequency cut. Each insight has a heading, brief description, actual analytical
code, generated findings summary and one chart or table. Seven figures and 14
tables use the same executed evidence in the notebook and website.

The approved [redesign plan](plan.md#notebook-and-theme-redesign-plan) and
[decision record](notes.md#2026-11-07--notebook-as-the-study-authoring-document)
establish notebook ownership. Theme text/order and publication selection are
declared in notebook metadata and checked against its visible theme cells.
Infrastructure helpers contain no study calculations or independent prose spec.

Install the optional notebook tools once with `./scripts/bootstrap --group notebooks`,
then select this workspace's `.venv` Python kernel in Cursor and run the notebook
from the start. Its [input lock](notebook-v2.inputs.lock.json) pins both retained
ledgers, source-run manifests and all 20 saved reference CSVs. Notebook outputs
are staged in a new `work/30_verniman_pivot_statistics_es/` directory on each run.
The selected measures are recalculated from retained event/day/section records;
86 exact saved-row comparisons check 308 value/support fields across all insights.
No website report JSON is loaded. This edition presents point estimates; earlier
ranked reports retain their uncertainty intervals. It reconstructs no vendor
events and tests no fills, costs or profitability.

The [V2 execution helper](notebook_v2.py) validates six-theme/question coverage,
visible source and rich outputs, and supplies actual fresh-kernel execution.
Focused numerical tests extract functions from the notebook's analysis cells:

```sh
./scripts/uv run --locked --no-sync python studies/30_verniman_pivot_statistics_es/notebook_v2.py check studies/30_verniman_pivot_statistics_es/vern-pivot-cross-statistics.ipynb --executed
./scripts/check-workspace --check study-30
```

For a new recorded execution, use `notebook_v2.py execute <source.ipynb> --output
work/30_verniman_pivot_statistics_es/<fresh-stage>/executed.ipynb --python
<workspace>/.venv/bin/python --cwd <workspace>`, with explicit `--input` pins
and an optional `--receipt`. The helper refuses existing destinations and keeps
the source notebook unchanged. Pin the active input lock, `uv.lock` and every
declared artifact with `--input`; retain the receipt and numerical comparisons.
Use `ABACUS_NOTEBOOK_INPUT_LOCK` to select its frozen lock copy and
`ABACUS_NOTEBOOK_OUTPUT_DIR` for a fresh output directory beneath study `work/`.

The [notebook exporter](publish_notebook.py) takes the current authoring notebook,
verified executed snapshot, execution receipt and
`--analysis-verification <outputs/saved-statistics-verification.json>`. An explicit
`--run-id` binds the analytical result. It writes one saved report per theme to
a new `--output` directory. `--retained-root` and `--retained-stage` project exact
source/output locators to the completed run before sealing. `--check <directory>`
checks the retained export inventory without executing analysis.

Export rejects stale source/input pins, failed/incomplete comparisons, private
paths, and undeclared output. Typed tables come from the same DataFrames as the
visible notebook tables; selected PNGs retain the exact executed bytes. Python
source, private setup and execution prompts do not enter public bundles. Narada
uses its strict report 1.1 contract and independent Node environment.

The completed V1 review execution remains under
`work/30_verniman_pivot_statistics_es/20261108T032043Z_notebook_v1_f7b7/`; its
[execution helper](notebook_v1.py), tests and input lock remain retained.

### Earlier saved-report readers — November 3

The earlier November 3 presentation uses the existing `20261031_ranked_v2` results:
one question heading, brief description, findings summary, then a saved chart or
compact supporting table. It contains 20 pivot insights and 12 VWAP insights.
The editable [Jupyter notebook](../../work/30_verniman_pivot_statistics_es/notebook/vern-pivot-cross-statistics.ipynb)
has one short setup cell, then normal Markdown/evidence cell pairs for each
insight. Saved data, a small display helper and eight original raster figures
sit beside it. Its outputs are already present; running cells redisplays the
same saved evidence using the Python standard library. Keep the notebook folder
together when moving it. No market-data access is needed.

The [completed readable copy](../../reports/exports/30_verniman_pivot_statistics_es/20261031_ranked_v2/20261103_readable_notebook_v3/vern-pivot-cross-statistics.ipynb)
is preserved separately. The earlier V2 single-file notebook is retained as a
historical presentation; its large embedded-data setup cell was unsuitable for
reading in editors that expose hidden cell inputs.

[Insight specifications](insight-spec.json) bind every displayed finding value
to a unique typed saved row. [Presentation input pins](insight-inputs.lock.json)
identify the unchanged sealed report sources, selected assets and run identity.
The [exporter](publish_insights.py) prepares new presentation revisions and
refuses existing destinations. Its read-only check replays the notebook code,
compares the cached rich outputs and verifies prepared bytes:

The [readable notebook producer](publish_readable_notebook.py) prepares the V3
folder from the completed V2 report sources and creates a separate editable copy
under `work/`. Its check verifies the completed copy independently of later
working edits. Every cell has ordinary visible source; the setup is 1,029
characters, with evidence stored in adjacent files rather than an encoded cell.

```sh
python3 studies/30_verniman_pivot_statistics_es/publish_insights.py --check
python3 studies/30_verniman_pivot_statistics_es/publish_readable_notebook.py --check
python3 -m unittest discover -s studies/30_verniman_pivot_statistics_es/tests -p 'test_insight*.py'
python3 -m unittest discover -s studies/30_verniman_pivot_statistics_es/tests -p 'test_readable_insight_notebook.py'
```

In those earlier reader notebooks, execution is presentation only. Compact tables retain the cited rows;
the earlier Ranked statistics reports retain their fuller saved tables and
filters. The two insight publications retain separate pivot-matched and
pivot-independent populations. No analytical methods, outcomes or completed
run files are changed. Later edits require new revision/publication identities.
Python code/output replay is separate from Jupyter frontend/kernel integration,
research revalidation and hosted deployment.

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

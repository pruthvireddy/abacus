# Anchored VWAP excursion and return study

The three-module historical study is implemented, executed and verified under
[frozen protocol 1.0.0](protocol-1.0.0.md). The selected reference run is
`20260929T234000Z_a15f`. This is descriptive research, not a profitability test.

- [Master report](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/report.html) · [Markdown](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/report.md)
- [Asia](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/asia.html) · [London](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/london.html) · [New York](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/ny.html) · [Globex](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/globex.html)
- [Findings and advice](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/advice.md)
- [Numerical verification](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/verification.json) · [Uncertainty verification](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/uncertainty-verification.json)
- All numerical tables: `runs/15_vwap_excursion_response/20260929T234000Z_a15f/tables/summary.csv` · [Coverage/exclusions](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/tables/coverage.csv)
- [Retained event evidence](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/events.manifest.json) · [Artifact manifest](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/manifest.json)
- [Post-seal completion checks](completion-verification.json)

The full `summary.csv` table is excluded from Git and requires exact-byte
restoration at the workspace-relative path above from a separately retained
copy. Its size and hash are recorded in the
[GitHub bulk artifact inventory](../../docs/github-bulk-artifacts.json).

ES, NQ and GC remain separate in all four session reports. Each covers departures
at 2/2.5/3 sigma, evolving/frozen VWAP returns, and first-touch bounce/through
response at 5/10/15/20/50 two-minute candles. The 15-candle horizon is supplementary.
The run contains 42,096 parents, 67,392 threshold signals and 35,843 first touches;
9,260 summary cells and 144 figures come from fresh saved outcomes.

The full feature-only pilot verified 2,096,910 two-minute bars before outcome
execution. Twenty research synthetic tests, 3,240 main-cell reconciliations,
1,888 independent raw-source horizon recounts and 120 independent interval checks
passed. The frozen-source hash check passed. Pre-existing catalog/package/older
study and run files remained unchanged in a 1,740-file preservation audit.

Coverage is sparse and retrospectively selected: 1,037 ES days, 1,177 NQ days and
825 GC days through 2026-09-18. The source has no true aggressor-volume delta.
No execution costs or profitability were tested. Static figures and HTML table
values/links were verified; browser-rendered HTML layout remains unverified
because the browser policy blocks local file URLs. Retained event copies are
hash-verified locally; an off-device backup has not been verified.

## Reproduce and inspect

Use the existing locked workspace environment. `--no-sync` avoids modifying its
installed package state; installed versions and the lock are captured in the run.
Use a new pilot/run path: existing completed runs must never be overwritten.
The numerical implementation and tests live in `src/` and `tests/` here.

```sh
UV_CACHE_DIR=/tmp/abacus-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/15_vwap_excursion_response/tests -p test_engine.py -v
UV_CACHE_DIR=/tmp/abacus-uv-cache ./scripts/uv run --locked --no-sync python -m unittest discover -s studies/15_vwap_excursion_response/tests -p test_inputs_stats.py -v
```

The exact executed pilot/run/summary/audit/render/seal commands are saved in
[commands.json](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/commands.json). Stage new execution under
`work/15_vwap_excursion_response/<new-run-id>/`. `pilot.py` verifies inputs and
feature coverage; `run.py` constructs events/outcomes; `summarize.py` creates
saved estimates; `verify.py` and `verify_uncertainty.py` independently audit;
`render.py` creates reports; `verify_reports.py` checks saved report content;
`qa_figures.cjs` rasterizes standalone SVGs for inspection; `seal.py` requires
completed verification records and preserves retained event files.

- [Original research plan](plan.md)
- [Original handoff prompt](handoff-prompt.md)
- [Current settings](study.yaml) · [Executable settings](protocol-1.0.0.json)
- [Pinned inputs](inputs.lock.json) · [Freeze record](freeze.json)
- [Decisions and assumptions](notes.md)

The reference run was selected after numerical reconciliation and report review,
not by recency or favorable outcomes. Older studies and runs are preserved.

## Sealing maintenance checks

[src/sealing.py](src/sealing.py) explicitly rejects failed/missing/malformed
verification records and incomplete execution before creating retained or
completed-run directories. Freeze validation and existing destination refusals
remain in place. Retained-copy and sealed-artifact hash mismatches fail under
ordinary and optimized Python and cannot produce a successful seal-verification
record. These gates do not make the copy process transactionally atomic: a later
failure can leave partial retained/completed output for manual investigation.

Synthetic tests patch the storage/freeze boundary and use temporary roots only:

```sh
./scripts/uv run --locked python -m unittest discover -s studies/15_vwap_excursion_response/tests -p 'test_sealing.py'
./scripts/uv run --locked python -O -m unittest discover -s studies/15_vwap_excursion_response/tests -p 'test_sealing.py'
```

The frozen numerical implementation, its tests, `freeze.json`, and existing
completed evidence are unchanged. Other analytical assertion checks remain
outside this maintenance scope.

## Chart indicator companion

A subsequent user request authorized the separate
[VWAP OE configurable-sigma fade statistics indicator](pine/README.md). It keeps the OE
visuals on the price chart and adds a lower-pane MAE/MFE diagram, horizon table,
independent cooldown comparisons and weekly opportunities. It computes from
loaded TradingView bars; it does not use old saved rates or execute the planned
historical study. Its every-close/fresh-cross options and inherited OE session
defaults are documented separately from the proposed research protocol.

The companion has configurable sigma distance and a session-start moratorium.
The [Pine source](pine/vwap_oe_fade_stats.pine) has passed 23 focused local scalar
helper tests; native TradingView compilation and replay remain unverified.
Run those checks with:

```sh
python3 -m unittest discover -s studies/15_vwap_excursion_response/tests -p 'test_pine_fade_stats.py' -v
```

See the [study guide](../AGENTS.md), [architecture](../../ARCHITECTURE.md), and
[evidence lifecycle](../../runs/README.md). The chart companion is separately
authorized; external publication, deployment and order execution are outside
the current scope.

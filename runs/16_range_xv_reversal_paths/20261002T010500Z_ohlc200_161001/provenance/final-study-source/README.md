# Range XV reversals and predictive lead-up

Protocol **2.0.0** is implemented and frozen. Local execution is in progress;
completed evidence will be linked after numerical/report verification and sealing.
The user's October 1 handoff authorizes the entire local lifecycle.

- [Full research plan](plan.md)
- [Executable choices fixed before outcomes](executable-protocol.md)
- [Settings](study.yaml)
- [Pinned input identities](inputs.lock.json)
- [Decisions and inspection history](notes.md)
- [Study entry point](run.py)

The universe is the eight pinned 6E/6B/6J/6S 4/5-setting exports. Exact fixed-point
OHLC comparisons supply direction/dojis. R is the first completed opposite bar
following a known uninterrupted leg; L excludes R and F counts consecutive
completed followers after R. Dojis and quality/session boundaries break legs.
Exact F requires a completed breaker; unknown prior starts and future censoring
remain separate. Short recent history stays in baseline/model rows with explicit
missing features and training-only preprocessing.

The main price path uses three physical future bars regardless of colour,
B1-open entry reference and B4-open exit mark, with gap-aware MAE/MFE excluding R.
Candle-order and strict positive-duration cohorts have separate denominators.
Enhanced timestamps are already inferred New York wall time and are not converted
again. Delta is signed price change; no volume/order-flow delta is present.

B0/B1/M1/M2 compare a constant baseline, R/context, added L and richer lead-up.
Development/validation/later dates are synchronized across charts. A selection
lock fixes development quartiles, penalties and at most three conditions before
later summaries. Prior inspection is disclosed. Models, price paths and assumed
cost sensitivities do not establish executable trading profitability.

No screenshots, OCR, ATAS/laptop control, browser automation or GUI inspection are
used. SVG charts render saved CSV evidence; programmatic checks reconcile values,
links, assets, source-row examples, score predictions and uncertainty.

## Reproduce from the workspace root

Use the locked workspace environment, a new unique run ID, and these stages:

```sh
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py prepare --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py freeze --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py execute --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py summarize --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python studies/16_range_xv_reversal_paths/run.py verify --out work/16_range_xv_reversal_paths/NEW_UNIQUE_RUN
```

After saving passing documentation/numerical/report checks to preseal-checks.json,
seal with the same entry point's `seal` stage. Mutable stages accept only staging
under work; completed runs cannot be rewritten. The `verify-sealed` stage performs
read-only checks of every sealed artifact and retained evidence checksum.

Focused tests and navigation gates:

```sh
UV_CACHE_DIR=.uv-cache OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 ./scripts/uv run --locked python -m unittest discover -s studies/16_range_xv_reversal_paths/tests -v
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
```

No dependency/shared-package/configuration change or Narada/UI work is involved.
The narrow study, documentation and navigation checks apply. See the [study
guide](../AGENTS.md), [Sahadeva guide](../../packages/sahadeva/AGENTS.md),
[architecture](../../ARCHITECTURE.md) and [run lifecycle](../../runs/README.md).

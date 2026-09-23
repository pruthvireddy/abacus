# Analysis 01: reversal-candle follow-through

This package audits and analyzes the filename-labeled ATAS Range XV exports for ES 4/5/6, GC10, and NQ10/20. It does not substitute the inventory-only GC6 file for missing GC20, reconstruct proprietary bars, or modify `data/`.

## Environment

Python 3.10 or newer with NumPy 2.x and pandas 2.2.x is required. The Codex desktop bundled Python used for the recorded run was:

```bash
/Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
```

For an independent environment, install the local package from the project root:

```bash
python3 -m venv analysis/01_reversal_follow_through/.venv
analysis/01_reversal_follow_through/.venv/bin/python -m pip install -e analysis/01_reversal_follow_through
```

## Commands

From `/Users/ppanati/Documents/projects/abacus-sahadeva`:

```bash
export PYTHONPATH=analysis/01_reversal_follow_through/src
python -m reversal_study.cli audit --config analysis/01_reversal_follow_through/configs/study.yaml
python -m reversal_study.cli run --config analysis/01_reversal_follow_through/configs/study.yaml
python -m reversal_study.cli report --config analysis/01_reversal_follow_through/configs/study.yaml --run-id <run_id>
```

To reproduce with the bundled environment without installing anything:

```bash
PYTHONPATH=analysis/01_reversal_follow_through/src /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m reversal_study.cli run --config analysis/01_reversal_follow_through/configs/study.yaml --run-id <unique_run_id>
```

Run tests:

```bash
PYTHONPATH=analysis/01_reversal_follow_through/src /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s analysis/01_reversal_follow_through/tests -v
```

## Frozen definitions

Direction is `sign(close-open)` in integer exchange ticks. A reversal is an immediately opposite non-doji bar within a valid provisional export-date segment. Dojis break runs. `L` counts following same-direction bars and excludes the reversal; `T=1+L`. The primary outcome is `P(L>=3)` among signals with three complete future bars. Incomplete windows are excluded rather than failed. The final row of every export is conservatively excluded because completion is unverified.

Development, validation, and test dates plus two one-export-date embargoes are frozen in `configs/study.yaml`. Candidate selection uses development only; validation applies fixed support checks; held-out test comparisons use paired export-date block bootstrap inference and Holm multiplicity control. The bootstrap uses 2,000 replicates and a recorded seed.

Event records go to `work/01_reversal_follow_through/<run_id>/events/`; normalized, source-row-preserving bars go to the neighboring `normalized/` directory. Reports, machine-readable tables, figures, methodology, data-quality findings, and the manifest go to `reports/01_reversal_follow_through/<run_id>/`.

Timing fields are raw timestamp-difference proxies only. The exports do not establish timezone, timestamp meaning, exact ATAS settings, bar-completion flags, or contract adjustment history.


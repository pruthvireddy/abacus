# Study 08: first countertrend Range XV bar

This study uses only the seven enhanced long-history Range XV files pinned in
[`inputs.lock.json`](inputs.lock.json). The [frozen plan](plan.md) and
[`study.yaml`](study.yaml) define the event, horizons, groups, exclusions, and
screen before outcome extraction. Older reports are context, not pooled input.

The completed local evidence is under
[`runs/08_countertrend_bar_continuation`](../../runs/08_countertrend_bar_continuation/).
The main answer is `P(C2 and C3 both follow C1)`; C1 itself is excluded from
the count of two more bars. Read the run's `report.md` and numerical CSVs together.

From the workspace root, using a new, sortable UTC run ID:

```sh
.venv/bin/python -m unittest discover -s studies/08_countertrend_bar_continuation/tests -v
.venv/bin/python studies/08_countertrend_bar_continuation/run.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/summarize.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/verify.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/render.py --stage work/08_countertrend_bar_continuation/<new-run-id>
.venv/bin/python studies/08_countertrend_bar_continuation/seal.py --stage work/08_countertrend_bar_continuation/<new-run-id>
```

`run.py` refuses an existing staging directory and verifies the exact manifest,
source, and enhanced hashes. The run ID must be new; completed runs are never
regenerated. The `verify.py` check reconciles source-row traces, manifest
counts, event ledgers, and saved table numerators/denominators. `render.py`
reads only saved evidence. `seal.py` snapshots the study code and environment
and moves the verified stage into `runs/` after creating the artifact manifest.

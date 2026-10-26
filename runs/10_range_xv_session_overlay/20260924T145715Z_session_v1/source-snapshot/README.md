# Study 10: Asia, London, and New York session overlay

This [exploratory plan](plan.md) compares decision-time segments in the saved
event ledgers of studies 07, 08, and 09. It preserves those completed runs.
The short-history study 07 clock is mapped to the corrected New York wall
time using its current enhanced files and the [migration record](../../docs/migration/range-xv-clock-normalization-20260924.json).
Study 07's clock-dependent quiet-breakout cohort itself is **not** recomputed.

The selected local evidence is in
[`runs/10_range_xv_session_overlay`](../../runs/10_range_xv_session_overlay/).
Read its report, tables, checks, and manifest together. All
three studies retain their own event population, outcome, and time horizon;
agreement across their settings is contextual rather than independent
validation. No web publication is part of this study.

From the workspace root, use a **new** sortable UTC run ID:

```sh
.venv/bin/python -m unittest discover -s studies/10_range_xv_session_overlay/tests -v
.venv/bin/python studies/10_range_xv_session_overlay/run.py --stage work/10_range_xv_session_overlay/<new-run-id>
.venv/bin/python studies/10_range_xv_session_overlay/verify.py --stage work/10_range_xv_session_overlay/<new-run-id>
.venv/bin/python studies/10_range_xv_session_overlay/render.py --stage work/10_range_xv_session_overlay/<new-run-id>
.venv/bin/python studies/10_range_xv_session_overlay/seal.py --stage work/10_range_xv_session_overlay/<new-run-id>
```

`run.py` verifies source hashes and refuses an existing stage. It reads saved
study ledgers; it never reruns or edits their completed directories. `verify.py`
reconciles segment counts and means to their original saved tables.

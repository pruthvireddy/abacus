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

## Future numerical-test evidence

Future stages require structured ordinary numerical-test success rather than a
literal suite length. Suite execution and stage evidence recording are separate.
Under separately authorized research/sealing scope:

```sh
./scripts/check-workspace --check study-10
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 10_range_xv_session_overlay --stage work/10_range_xv_session_overlay/<new-run-id>
./scripts/uv run --locked --no-sync python scripts/record-numerical-tests.py --study 10_range_xv_session_overlay --stage work/10_range_xv_session_overlay/<new-run-id> --check
./scripts/uv run --locked --no-sync python studies/10_range_xv_session_overlay/seal.py --stage work/10_range_xv_session_overlay/<new-run-id>
```

Only an explicit `--legacy-test-log` option permits an old log-only stage, keeping
the original six-test check and labelling it unbound to tested source. A failed,
invalid or incomplete structured attempt cannot use legacy fallback. The 34-input
and 24 referenced-ledger checks remain scientific requirements. See
[future-stage evidence](../README.md#future-stage-evidence) for strict record
types, source/lock/log binding and limits. Existing completed evidence is preserved.

# Study 09: C2 confirmation after a first countertrend Range XV bar

This study uses the seven pinned enhanced long-history Range XV files in
[`inputs.lock.json`](inputs.lock.json). The [plan](plan.md) and
[`study.yaml`](study.yaml) froze the candidate, ordinary baseline, common C1
opportunity set, price references, exclusions, and 70-cell screen before
extraction. The age-two ordinary baseline in [notes](notes.md) is an explicitly
post-result diagnostic. Study 08 motivates the question but is not an event
input.

The completed local evidence is under
[`runs/09_range_xv_c2_confirmation`](../../runs/09_range_xv_c2_confirmation/).
The primary chart-behavior outcome is `P(C3 and C4 both follow C1 | C2
confirms)`, compared at C2 completion with an ordinary same-direction B1/B2
pair. For the decision to wait, use the common-C1 opportunity tables and
price proxy alongside the conditional result. Read the run's report and saved
CSV tables together.

From the workspace root, use a **new** sortable UTC run ID:

```sh
.venv/bin/python -m unittest discover -s studies/09_range_xv_c2_confirmation/tests -v
.venv/bin/python studies/09_range_xv_c2_confirmation/run.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/summarize.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/verify.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/render.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
.venv/bin/python studies/09_range_xv_c2_confirmation/seal.py --stage work/09_range_xv_c2_confirmation/<new-run-id>
```

`run.py` refuses an existing stage and verifies exact input hashes. `verify.py`
reconciles ledger counts, source rows, timing, numeric tables, and price means.
`render.py` reads saved numerical evidence. `seal.py` snapshots this study's
code and environment and moves the checked stage into a unique local run.
Completed runs must not be regenerated.

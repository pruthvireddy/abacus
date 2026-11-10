# Daily Facts volume pilot

The notebook compares first-hour and last-hour volume on the same asset and
session. It uses the six-window Daily Facts 1.0.0 release and displays the actual
denominators for ES, NQ and GC.

The [protocol](plan.md), [settings](study.yaml), [input lock](inputs.lock.json)
and [decisions](notes.md) describe the pilot. Use the
[authored notebook](daily-facts-volume-pilot.ipynb) for editing and the
[executed notebook](../../runs/31_daily_facts_volume_pilot/20261108T234605Z_daily_facts_v1/daily-facts-volume-pilot.ipynb)
for saved results. The [local report](../../runs/31_daily_facts_volume_pilot/20261108T234605Z_daily_facts_v1/report.html)
and [parity record](../../runs/31_daily_facts_volume_pilot/20261108T234605Z_daily_facts_v1/verification.json)
come from that sealed run.

Use the existing locked notebooks environment and the retained release named in
the input lock. From the workspace root, choose a fresh sortable UTC run ID.
The runner starts a local Jupyter kernel using a Unix socket and needs local
socket permission. The runner compares saved tables against pinned Arrow rows
using independent integer and rational arithmetic, then checks the evidence
bundle before sealing it.

```sh
./scripts/uv run --locked --no-sync python -B studies/31_daily_facts_volume_pilot/run.py --run-id <new-utc-run-id>
python3 scripts/check-evidence-bundle.py runs/31_daily_facts_volume_pilot/20261108T234605Z_daily_facts_v1
```

The [release quality record](../../reports/quality/daily_market_facts__1.0.0.md)
describes source-level numerical verification. The notebook's parity check
covers consumer calculations on the released rows. The estimates are descriptive
and use different product calendars and qualifying dates.

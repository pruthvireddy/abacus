# NQ Overnight Range at the Cash Open

Study 32 measures which overnight boundaries NQ reaches during the regular
session and how the results vary with opening location, width, volatility,
era and year. The six-theme notebook covers the reel comparison, path and
timing, distance controls, pre-open VXN/VIX, 2015–2019 versus 2020 onward,
and 2023–2026 by year. The 2026 data end on September 18.

Review the [executed notebook](../../runs/32_nq_overnight_range/20261110T134251Z_review_nq_v2/nq-overnight-range-cash-open.ipynb)
or [local reading copy](../../runs/32_nq_overnight_range/20261110T134251Z_review_nq_v2/report.html).
The [frozen protocol](plan.md), [settings](study.yaml), [input lock](inputs.lock.json)
and [decisions](notes.md) define the analysis. The
[verification receipt](../../runs/32_nq_overnight_range/20261110T134251Z_review_nq_v2/verification.json)
records the notebook and outcome reconciliations. The results describe the
retained sample without modeling orders or fills.

The [Bhishma feature release](../../catalog/datasets/nq_opening_range_facts__1.0.0.json)
and [Postgres receipt](../../reports/quality/nq_opening_range_facts__1.0.0__postgres_parity.json)
identify the reusable opening features. Read the
[coverage record](../../reports/quality/nq_opening_range_facts__1.0.0.json) before
interpreting the early era. 2018–2019 contribute 295 of its 307 inside-range sessions.

Use a fresh sortable UTC run ID with the locked notebook environment. Jupyter
requires local Unix socket permission.

```sh
./scripts/check-workspace --check study-32
./scripts/uv run --locked --no-sync python -B studies/32_nq_overnight_range/run.py --run-id <new-utc-run-id>
```

The authored [notebook](nq-overnight-range-cash-open.ipynb) contains the
calculations. The local HTML reading copy is generated from the same executed
cells and figures. The [Narada edition](https://abacus-narada.vercel.app/studies/nq-overnight-range-cash-open/)
uses the six verified presentation revisions projected from that sealed run.
The [notebook exporter](publish_notebook.py) binds the selected output to the
execution receipt and verifies its typed tables and exact PNG bytes.

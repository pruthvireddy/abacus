# Range XV edge candidates

Three frozen chart-price hypotheses on ES 6RXV, NQ 20RXV, and GC 20RXV. The seven original ATAS exports are pinned by SHA-256. Their timestamp timezone and exact bar-completion times are unverified.

The sealed `20260924T004900Z_rxv07` run used the earlier enhanced CSV bytes.
Those results and `inputs.lock.json` remain historical. The enhanced CSVs at
their existing paths were clock-normalized on 2026-09-24; see the
[migration crosswalk](../../docs/migration/range-xv-clock-normalization-20260924.json).
The original export clock appears to be fixed UTC−04:00, so winter timestamps
in the sealed run's 09:30–10:30 export-clock subgroup were not New York time.
Any new study must pin the current manifest/hash and use a new protocol and
run ID. The command below retains the historical input lock and will reject
the corrected files until the study is explicitly revised.

[Plan](plan.md) · [Corrected settings](protocol-1.0.1.json) · [Input lock](inputs.lock.json) · [Decision log](notes.md)

Run a new unique UTC ID only; never overwrite a completed run:

```sh
.venv/bin/python -m unittest discover -s studies/07_range_xv_edge_candidates/tests -v
.venv/bin/python studies/07_range_xv_edge_candidates/run.py --run-id NEW_UNIQUE_ID
.venv/bin/python studies/07_range_xv_edge_candidates/verify.py --run-id NEW_UNIQUE_ID
.venv/bin/python studies/07_range_xv_edge_candidates/seal.py --run-id NEW_UNIQUE_ID
```

The run writes primary and secondary event ledgers, cost and tail tables, an offline report, dated advice, and a checksum manifest. Findings are retrospective; fresh unseen data and fill-level evidence are needed for an executable-edge claim.

Reference evidence: [`20260924T004900Z_rxv07`](../../runs/07_range_xv_edge_candidates/20260924T004900Z_rxv07/report.md). No primary comparison passes the declared candidate screen.

A later [Asia/London/New York overlay](../10_range_xv_session_overlay/README.md)
maps these sealed event outcomes to corrected decision-time labels and retains
the original clock-dependent quiet-breakout calibration as a limitation.

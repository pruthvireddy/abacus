# Range XV edge candidates

Three frozen chart-price hypotheses on ES 6RXV, NQ 20RXV, and GC 20RXV. The seven original ATAS exports are pinned by SHA-256. Their timestamp timezone and exact bar-completion times are unverified.

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

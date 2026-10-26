# Session-anchored VWAP

Study `05_session_vwap` · **three candidates evaluated** · ES / NQ / GC

The selected statistical price-path studies are return to VWAP after departure (`vwap_return_after_departure`), fade of the first close outside 2σ (`vwap_extreme_fade`), and bounce on the first causal VWAP retest (`vwap_first_retest_bounce`). The [original six-candidate plan](plan.md) remains historical context. Re-entry fades, cross acceptance/retests, and outside-band continuation remain proposed and have no computed outcomes in this run.

[Protocol 1.0.0](protocol-1.0.0.md) fixes the executed definitions, populations, causal timing, three primary statistics, baselines, splits, and sensitivity checks. [study.yaml](study.yaml) records the selected scope. The [strategy cards](../../strategies/README.md) distinguish the three evaluated ideas from the three unexecuted proposals.

## Inputs and status

[inputs.lock.json](inputs.lock.json) pins the immutable Bhishma `session_anchored_vwap__1.0.0` release, its 2m/5m datasets, and unadjusted one-minute source. Storage resolves through Abacus path configuration; the current publication root is this workspace. Input identity and consumed partition checksums are verified for each extraction. The [storage relocation](../../docs/migration/storage-relocation-20260922.md) changes physical storage without changing the pinned release.

The reference execution is `20260923T015900Z_vwap3`. Its [report](../../runs/05_session_vwap/20260923T015900Z_vwap3/report.html), [metrics](../../runs/05_session_vwap/20260923T015900Z_vwap3/metrics.json), [event evidence](../../runs/05_session_vwap/20260923T015900Z_vwap3/events.manifest.json), and [manifest](../../runs/05_session_vwap/20260923T015900Z_vwap3/manifest.json) are retained under `runs/` after verification. The [decision history](notes.md) records execution changes and inspected variants. Findings concern conditional movement; fills, costs, latency, and sizing remain unspecified.

## Reproduce

From the workspace root, use a fresh run ID with `.venv/bin/python studies/05_session_vwap/run.py --run-id <new-id> --workers 3`. Then run `enrich.py`, `audit.py`, and `summarize.py` with that ID; inspect the output before sealing. The saved run manifest records the exact commands, code snapshot, environment, input hashes, and artifact hashes. Run IDs must be unique; never overwrite a completed run or published input.

[Artifact conventions](../../templates/README.md) · [Research library](../../reports/index.html)

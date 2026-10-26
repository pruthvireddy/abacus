# Session-anchored VWAP

Study `05_session_vwap` · **three primary candidates evaluated; A/C context explored** · ES / NQ / GC

The original statistical price-path studies are return to VWAP after departure (`vwap_return_after_departure`), fade of the first close outside 2σ (`vwap_extreme_fade`), and bounce on the first causal VWAP retest (`vwap_first_retest_bounce`). The [original six-candidate plan](plan.md) remains historical context. Re-entry fades now have partial exploratory evidence; a paired wait-versus-immediate policy comparison is outstanding. Cross acceptance/retests and outside-band continuation remain proposed.

[Protocol 1.0.0](protocol-1.0.0.md) fixes the original executed definitions, populations, causal timing, three primary statistics, baselines, splits, and sensitivity checks. [Protocol 1.1.0](protocol-1.1.0.md) freezes the later exploratory A/C context cuts, including NY first 30/60 minutes, prior excursion, opening balance, ATR, and re-entry. [study.yaml](study.yaml) records the selected scope.

## Inputs and status

[inputs.lock.json](inputs.lock.json) pins the immutable Bhishma `session_anchored_vwap__1.0.0` release, its 2m/5m datasets, and unadjusted one-minute source. Storage resolves through Abacus path configuration; the current publication root is this workspace. Input identity and consumed partition checksums are verified for each extraction. The [storage relocation](../../docs/migration/storage-relocation-20260922.md) changes physical storage without changing the pinned release.

The reference execution is `20260923T015900Z_vwap3`. Its [report](../../runs/05_session_vwap/20260923T015900Z_vwap3/report.html), [metrics](../../runs/05_session_vwap/20260923T015900Z_vwap3/metrics.json), [event evidence](../../runs/05_session_vwap/20260923T015900Z_vwap3/events.manifest.json), and [manifest](../../runs/05_session_vwap/20260923T015900Z_vwap3/manifest.json) are retained under `runs/` after verification. The [decision history](notes.md) records execution changes and inspected variants. Findings concern conditional movement; fills, costs, latency, and sizing remain unspecified.

The later exploratory execution is `20260923T035300Z_ac_context`. Its [report](../../runs/05_session_vwap/20260923T035300Z_ac_context/report.html), [all cuts](../../runs/05_session_vwap/20260923T035300Z_ac_context/tables/cuts.csv), [NY early exits](../../runs/05_session_vwap/20260923T035300Z_ac_context/tables/ny_early.csv), and [run advice](../../runs/05_session_vwap/20260923T035300Z_ac_context/advice.md) link back to the unchanged parent event ledger. The selected segments are discovery evidence because final-period outcomes had already been viewed.

## Reproduce

From the workspace root, use a fresh run ID with `.venv/bin/python studies/05_session_vwap/run.py --run-id <new-id> --workers 3`. Then run `enrich.py`, `audit.py`, and `summarize.py` with that ID; inspect the output before sealing. The saved run manifest records the exact commands, code snapshot, environment, input hashes, and artifact hashes. Run IDs must be unique; never overwrite a completed run or published input.

For the context study, use a fresh ID with `.venv/bin/python studies/05_session_vwap/conditional_run.py --run-id <new-id> --workers 3`, followed by `conditional_audit.py` and `conditional_summarize.py`. Its saved run manifest records the checks and source snapshot.

[Artifact conventions](../../templates/README.md) · [Research library](../../reports/index.html)

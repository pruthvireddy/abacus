# VWAP state dynamics

Study `06_vwap_state_dynamics` evaluates three fixed 30-minute probability questions on the pinned Session-Anchored VWAP 1.0.0 release. The primary population is ES, NQ, and GC at regular half-hour New York clock landmarks using the 2-minute Globex anchor. Local Asia/London/NY anchors and the independent 5-minute Globex calculation are separate replications. All available periods are exploratory because study 05 VWAP outcomes were previously viewed.

[Plan](plan.md) · [Frozen protocol](protocol-1.0.0.md) and [executable settings](protocol-1.0.0.json) · [Input lock](inputs.lock.json) · [Decision history](notes.md)

The first execution is `20260923T180000Z_state06c`. Its [offline report](../../runs/06_vwap_state_dynamics/20260923T180000Z_state06c/report.html), [probability atlas](../../runs/06_vwap_state_dynamics/20260923T180000Z_state06c/tables/probability_atlas.csv), [event evidence manifest](../../runs/06_vwap_state_dynamics/20260923T180000Z_state06c/events.manifest.json), and [dated advice](../../runs/06_vwap_state_dynamics/20260923T180000Z_state06c/advice.md) are retained together. The run's `manifest.json` records the exact commands, source snapshot, input hashes, checks, and output hashes. No public Narada bundle was created or deployed.

## Reproduce

Use the locked workspace environment and a **new unique run ID**. Run the feature-only gate and inspect its distributions, freeze a versioned JSON protocol referring to that gate ID, then run `join_audit.py`, `run.py`, `summarize.py`, `audit.py`, and `render.py` in that order. The first run's exact commands and cutoffs are in its report and manifest. Focused numerical tests:

```sh
.venv/bin/python -m unittest discover -s studies/06_vwap_state_dynamics/tests -v
```

Do not rerun an archived or sealed run into its original location. The plan's five secondary exploratory modules were not executed in protocol 1.0.0 and require a separate frozen amendment or run.

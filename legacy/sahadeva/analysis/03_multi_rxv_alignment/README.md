# Multi-Range-XV alignment study

This study aligns smaller and larger ATAS Range XV exports without look-ahead.
It evaluates trend-aligned pullback continuation, countertrend early reversal
signals, larger-run exhaustion, and repeated small-chart warning attempts.

Run from the project root with the bundled analysis environment:

```bash
/Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 analysis/03_multi_rxv_alignment/run_study.py
```

The fixed study design is in `config.json`. Results are written to
`reports/03_multi_rxv_alignment/20260908T_multi_rxv_v1/`.

Start with `summary.md` in that folder. The detailed event-study results and
session-cluster confidence intervals are in its `tables/` directory.

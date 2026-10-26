# Range XV reversals and predictive lead up

Status: **planned**, proposed protocol **2.0.0**. No study outcomes have been
extracted. This revision prepares the full OHLC-only study and a copyable prompt;
the receiving agent is authorized to implement and run it when given that prompt.

- [Full research plan](plan.md)
- [Copyable agent handoff](handoff-prompt.md)
- [Proposed settings](study.yaml)
- [Pinned input identities](inputs.lock.json)
- [Decisions and assumptions](notes.md)

Use the eight newly imported 6E/6B/6J/6S 4/5 Range XV charts. Direction and
reversal labels come directly from exact OHLC comparisons. No ATAS interaction,
screenshots, OCR, browser automation, laptop control, or visual pattern labelling
is required or permitted. Generate report figures from saved numerical evidence
and validate files programmatically.

R is the first completed opposite-direction non-doji candle after a known leg;
L counts its preceding candles and F counts followers after R, excluding R.
The main price horizon is three physical future bars including failures,
with entry B1 open and exit mark B4 open. Measure signed price delta, MAE/MFE,
tail risk and elapsed proxy time. Delta does not mean unavailable volume delta.

The revised plan tests whether L, leg pace/shape/efficiency, recent chop and
R geometry add predictive information beyond ordinary reversals. It includes
chronological development/validation/later evaluation, simple model comparisons,
frozen interpretable conditions, matched baselines, censor/quality diagnostics
and a mandatory Swiss franc tick-era split. Continuation is a hypothesis;
chart construction and a completed pre-signal price move do not prove an edge.

Methodological context: [study 08](../08_countertrend_bar_continuation/plan.md)
and [study 09](../09_range_xv_c2_confirmation/plan.md). Preserve their sealed
evidence. The [FX import guide](../../docs/range-xv-fx-20261001.md) describes
columns, timing, volume and provenance limitations.

Proposed implementation belongs in local run.py, src/ and tests/. Those entry
points do not exist yet. Stage a unique work/16_range_xv_reversal_paths/<run-id>
and seal verified evidence under the corresponding new runs/ directory. The
receiving agent documents actual commands after implementation. No reference
run or tested trading rule is selected.

Planning-only checks from the workspace root:

```sh
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
```

Follow the [study guide](../AGENTS.md), [Sahadeva guide](../../packages/sahadeva/AGENTS.md),
[architecture](../../ARCHITECTURE.md), and [evidence lifecycle](../../runs/README.md).

# Analysis 02: adverse movement of the second same-direction candle

This study covers all seven available filename-labeled Range XV exports: ES 4/5/6, GC 6/10, and NQ 10/20. It leaves Analysis 01 unchanged.

The reversal candle is the first same-direction candle. The immediately following candle is sequence position 2. The primary cohort requires that this candle exist in the same provisional export-date segment and also close in the reversal direction. Primary adverse movement is open-to-low for green/long and high-to-open for red/short. A separate sensitivity uses the reversal close as the reference.

## Run

From `/Users/ppanati/Documents/projects/abacus-sahadeva`:

```bash
PYTHONPATH=analysis/02_followthrough_candle_adverse/src /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m followthrough_adverse.cli run --config analysis/02_followthrough_candle_adverse/configs/study.yaml --run-id <unique_run_id>
```

## Test

```bash
PYTHONPATH=analysis/02_followthrough_candle_adverse/src /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s analysis/02_followthrough_candle_adverse/tests -v
```

The full-period headline includes every reversal with at least one immediately preceding opposite non-doji candle. Long/short results, prior-run minimum 2 and 3 sensitivities, and chronological stability slices are separate. Mean 95% confidence intervals use 2,000 export-date block bootstrap replicates with the frozen seed.

The time-of-day extension uses exact 30-minute raw export-clock buckets. It reports reversal-time follow-through probability and geometry separately from follow-through confirmation-time concentration. Because the exports do not identify a timezone or timestamp convention, no ET/CT conversion or open/close timestamp claim is made. Supported rankings require at least 200 conditioned events and 10 active export dates per half-hour.

The post-confirmation hold-time extension asks whether the next two bars also close in the established direction and measures the raw timestamp difference to the second additional bar among successes. A separate 20-bar sensitivity finds the first later same-direction pair while allowing intervening bars. Both probabilities use only complete same-segment horizons. All minute values remain explicitly labeled as timestamp-difference proxies.

The corrected full-leg extension starts at the reversal candle and measures the uninterrupted same-direction run through its final candle before the next opposite candle. Its primary cohort contains completed legs with at least three candles including the reversal. Results include overall duration, 30-minute reversal-time windows, export-date block confidence intervals, and exact candle-count summaries. Censored export-date-boundary legs are excluded.

Event-level records are written under `work/02_followthrough_candle_adverse/<run_id>/events/`. Reports, CSV summaries, figures, methodology, data quality, and the manifest are written under `reports/02_followthrough_candle_adverse/<run_id>/`. Source files in `data/` are never modified.

# VWAP conditional probabilities — study plan

Prepared 2026-09-24. The user authorized feature inspection, protocol freeze,
implementation, execution, verification, reporting, and sealing. No indicator,
publication, deployment, order placement, or profitability study is in scope.

## Questions

### A. Remaining return probability

Create fresh, rearmed departure episodes after a mature anchor first closes at
least one sigma and four ticks from VWAP. At ten-minute New York clock
checkpoints, retain only episodes with no causal contact or gap-through of the
previously known evolving VWAP zone. Estimate contact with checkpoint-frozen
VWAP within 30 elapsed minutes and by the observation-window end. Report causal
evolving-VWAP contact separately, including evolving-only contacts.

The central comparison is whether elapsed survival time and observed path state
add forecast information beyond current distance, product, anchor, clock, time
remaining, and prior-only volatility.

### B. Return versus extension

Use the same at-risk checkpoints. Starting with the first one-minute bar after
the completed checkpoint, race the checkpoint-frozen VWAP ± one tick against a
further 0.5 checkpoint sigma move from the checkpoint close. Preserve return
first, extension first, neither, same-minute ambiguous, gap, and unavailable
classes. Compare with geometry-aware earlier-history estimates and retain small
0.25- and 1.0-sigma sensitivities.

### C. Day VWAP and active-session VWAP

After a completed-close cross through a mature Asia, London, or NY VWAP, require
price to remain strictly between mature Globex and local-session VWAP zones.
Freeze both references. Race day VWAP against a reclaim of session VWAP for 30
minutes, with mirrored upper/lower configurations. A fixed 30-minute event
lockout suppresses repeated crosses without consulting future outcomes.

The feature-only gate selects one minimum corridor-separation rule from declared
tick and day-sigma candidates using support only. The baseline uses target
distance, corridor position/width, product, session, clock, and prior volatility.
The only added path features are prior hold duration, agreement of past-only day
and session VWAP slopes, and past-only corridor widening/narrowing.

## Shared population and timing

- Inputs are the immutable two- and five-minute feature release plus matching
  unadjusted one-minute source pinned in `inputs.lock.json`.
- ES, NQ, and GC remain separate in primary reporting. Pooled summaries are
  secondary and use shared-week uncertainty blocks.
- A/B use Globex and the active local anchor only within its published membership
  window. C uses Globex plus exactly one active local anchor.
- Anchor warm-up is 30 elapsed minutes. A 30-minute state/slope lookback first
  becomes available after 60 elapsed anchor minutes; missing early context stays
  explicit.
- Features are available only at `available_at`, the exclusive completed-bar
  close. Future observation starts at the next unadjusted one-minute bar open.
- Complete-day eligibility is retrospective sample selection, never a live
  feature. Missing bars, contract changes, rolls, and incomplete horizons remain
  unavailable rather than false.
- Development ends 2023, 2024 is a chronological validation label, and 2025–2026
  is a chronological final label. None is a pristine holdout.

## Feature-only gate

The pilot may inspect release identity, feature availability, counts, clocks,
current/past-only distributions, contract keys, and corridor support under the
declared separation candidates. It must not read future one-minute paths or
calculate any future target outcome. The chosen corridor rule, distance bins,
ATR terciles, model support floor, comparisons, and report schema are frozen in
`protocol-1.0.0.json` before `run.py` can execute.

## Estimation

Raw estimates state population, condition, event, horizon, numerator,
denominator, unresolved/ambiguous/unavailable counts, and a 95% shared-ISO-week
bootstrap interval. Repeated checkpoints are rows but episodes, product-sessions,
and weeks are also reported.

Prediction comparisons use development-only supported conditional estimators.
A baseline cell is defined only by geometry, product/anchor, clock, and prior
volatility. The augmented estimate adds the small declared path-state set and
falls back to the baseline when development support is below the frozen floor.
Transformations and bins are fixed before validation/final prediction. Report
multiclass Brier score, calibration, coverage of the more specific estimator,
and shared-week uncertainty for score differences.

No rate is a trade win rate. Unequal barrier geometry makes 50% an invalid
neutral benchmark for Question B. No superiority claim is planned across the
three-question family.

## Required evidence and checks

Save feature-only candidates, event/checkpoint outcomes, updated corridor
landmarks, support/exclusion/model/calibration tables, deterministic chart
examples, figures, report, advice, display specification, exact commands,
source snapshot, input hashes, and artifact hashes. Tests and independent source
recounts cover no-return, later return, evolving-only contact, signal-bar
exclusion, same-minute ambiguity, gaps, immature anchors, missing bars, repeated
checkpoints/crosses, mirrored corridors, contract changes, and null semantics.


# VWAP state dynamics advice — 2026-09-23

Status: exploratory research interpretation. All currently available dates had prior VWAP-outcome exposure. This is not an executable strategy or a net-profitability claim.

## Strongest positive conditional probability

The 2-minute Globex persistent-side state had 83.3% 30-minute causal-VWAP residence versus 39.2% for rotational state. The raw +44.1 percentage-point gap shrank to +18.7 pp (95% shared-date CI +15.5 pp to +22.0 pp) within common product, side, distance, clock, prior-ATR, and age strata. Support retained 96,078/104,577 persistent and 4,173/4,236 rotational landmarks. This is evidence of conditional path association, not an edge after transaction costs. See `tables/primary_probabilities.csv` and `tables/matched_comparisons.csv`, Q1/ALL/all.

VWAP beat the paired same-anchor TWAP reference on 89,056/133,716 common timestamps (66.6%; 95% CI 65.9%–67.3%). On materially separated references this rose to 71.7%. However the last known price had lower mean absolute error than either anchored reference in ES, NQ, and GC, and local-anchor replications did not consistently favor VWAP. See `tables/paired_errors.csv` and `tables/replications.csv`.

## Negative and inconclusive findings

Opposing price/VWAP slopes produced only +2.1 pp incremental 30-minute crossing probability after matching on residence state and context (95% CI +1.0 pp to +3.2 pp). NQ and GC intervals nearly touch zero, and the 2024 label spans zero. No familywise-adjusted or baseline-model incremental forecasting claim is justified.

For a favorable-first price move, persistent versus rotational was +0.9 pp at fixed 8 ticks (CI includes zero), but -8.4 pp at the ceiling-rounded half-sigma barrier. Opposing versus aligned was -0.4 pp at 8 ticks (CI includes zero), versus -3.3 pp at half-sigma. The barrier-dependent ordering prevents treating VWAP residence or slope state as a universal directional edge. Same-minute barrier ambiguity remains in the denominator. See `tables/barrier_comparisons.csv` and `tables/barrier_outcomes.csv`.

## Decision and next research action

Retain Q1 residence as a descriptive state feature for a later genuinely uninspected period. Do not promote Q2 or the paired reference advantage to a trade rule. Freeze a simple baseline model using product, clock, distance, and prior ATR before any claim of incremental prediction; evaluate future untouched dates with shared-date uncertainty and a declared familywise procedure if superiority is asserted. The plan's five additional ideas are unexecuted exploratory modules and require separate frozen protocols. Costs, fills, sizing, and net P&L remain untested.

## 2026-09-23 exploratory reporting supplement

First-cross timing, explicit clock gaps, and secondary paired targets are in this run's report and tables. They do not change the parent primary decision or establish an execution edge.

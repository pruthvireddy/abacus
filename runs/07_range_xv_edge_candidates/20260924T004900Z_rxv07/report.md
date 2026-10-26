# Range XV edge candidates — 20260924T004900Z_rxv07

Computed 2026-09-24T00:48:36.600635+00:00. Chart-price research on the seven pinned ATAS exports; three primary charts. All calendar blocks were previously inspected by earlier studies, so the last block is retrospective.

**Result: 0 of 9 primary idea-by-asset comparisons pass the declared candidate screen.** The development block calibrates the quiet-period threshold and is in-sample. The later blocks use that prior calibration, but were already viewed in earlier research.

## Primary results

One- or three-future-bar signed open-to-open returns in ticks, using the next bar start as the signal-completion proxy. Net figures deduct two ticks per executed round trip. Wait-policy opportunities that never confirm remain in its denominator with zero return and no cost.

| product | idea | cohort | split | opportunities | trades | sessions | mean_ticks | mean_net_2_ticks | p05_ticks | break_even_cost_ticks_per_trade |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ES | pullback | extreme_break | all | 9731 | 9731 | 532 | -0.185 | -2.185 | -28.000 | -0.185 |
| ES | pullback | no_break | all | 1006 | 1006 | 362 | -0.333 | -2.333 | -28.000 | -0.333 |
| ES | pullback | ordinary | all | 44552 | 44552 | 533 | -0.252 | -2.252 | -14.000 | -0.252 |
| ES | pullback | unfiltered | all | 10737 | 10737 | 532 | -0.199 | -2.199 | -28.000 | -0.199 |
| ES | exhaustion | early_policy | all | 4623 | 4623 | 510 | -0.126 | -2.126 | -35.000 | -0.126 |
| ES | exhaustion | short_run_control | all | 25504 | 25504 | 534 | -0.255 | -2.255 | -37.000 | -0.255 |
| ES | exhaustion | wait_policy | all | 4623 | 3287 | 510 | -0.104 | -1.526 | -28.000 | -0.146 |
| ES | quiet_breakout | not_quiet | all | 25753 | 25753 | 498 | -0.349 | -2.349 | -28.000 | -0.349 |
| ES | quiet_breakout | quiet | all | 6894 | 6894 | 527 | -0.550 | -2.550 | -28.000 | -0.550 |
| NQ | pullback | extreme_break | all | 25806 | 25806 | 534 | -0.473 | -2.473 | -87.000 | -0.473 |
| NQ | pullback | no_break | all | 866 | 866 | 374 | 2.418 | 0.418 | -87.000 | 2.418 |
| NQ | pullback | ordinary | all | 112442 | 112442 | 534 | -0.598 | -2.598 | -45.000 | -0.598 |
| NQ | pullback | unfiltered | all | 26672 | 26672 | 534 | -0.379 | -2.379 | -87.000 | -0.379 |
| NQ | exhaustion | early_policy | all | 12308 | 12308 | 531 | -1.024 | -3.024 | -107.000 | -1.024 |
| NQ | exhaustion | short_run_control | all | 61791 | 61791 | 534 | -0.255 | -2.255 | -126.000 | -0.255 |
| NQ | exhaustion | wait_policy | all | 12308 | 8570 | 531 | -1.248 | -2.641 | -86.000 | -1.793 |
| NQ | quiet_breakout | not_quiet | all | 70059 | 70059 | 526 | -0.862 | -2.862 | -87.000 | -0.862 |
| NQ | quiet_breakout | quiet | all | 12276 | 12276 | 512 | -1.155 | -3.155 | -85.000 | -1.155 |
| GC | pullback | extreme_break | all | 6455 | 6455 | 504 | 0.428 | -1.572 | -90.000 | 0.428 |
| GC | pullback | no_break | all | 197 | 197 | 117 | -1.736 | -3.736 | -93.000 | -1.736 |
| GC | pullback | ordinary | all | 28634 | 28634 | 532 | -0.216 | -2.216 | -47.000 | -0.216 |
| GC | pullback | unfiltered | all | 6652 | 6652 | 505 | 0.364 | -1.636 | -90.000 | 0.364 |
| GC | exhaustion | early_policy | all | 3010 | 3010 | 445 | 0.142 | -1.858 | -109.000 | 0.142 |
| GC | exhaustion | short_run_control | all | 15782 | 15782 | 533 | -0.519 | -2.519 | -126.000 | -0.519 |
| GC | exhaustion | wait_policy | all | 3010 | 2126 | 445 | 0.329 | -1.084 | -87.000 | 0.466 |
| GC | quiet_breakout | not_quiet | all | 18972 | 18972 | 505 | -0.194 | -2.194 | -90.000 | -0.194 |
| GC | quiet_breakout | quiet | all | 1861 | 1861 | 502 | -0.861 | -2.861 | -85.000 | -0.861 |

## Matched contrasts

The difference is candidate minus control after two ticks per executed trade. Session-cluster bootstrap intervals use 99.44% familywise coverage for the nine primary comparisons. Differing opportunity populations are not causal matches.

The pullback baseline includes the extreme-break candidate, as specified in the original plan. The nonbreak complement is shown as descriptive context; it is much smaller on these Range XV charts.

| product | idea | gross_difference_ticks | difference_ticks | lower | upper | n_sessions |
| --- | --- | --- | --- | --- | --- | --- |
| ES | pullback | 0.014 | 0.014 | -0.132 | 0.159 | 532 |
| ES | exhaustion | 0.022 | 0.600 | -0.164 | 1.443 | 510 |
| ES | quiet_breakout | -0.201 | -0.201 | -0.995 | 0.588 | 533 |
| NQ | pullback | -0.094 | -0.094 | -0.219 | 0.031 | 534 |
| NQ | exhaustion | -0.224 | 0.383 | -1.086 | 1.950 | 531 |
| NQ | quiet_breakout | -0.293 | -0.293 | -1.794 | 1.308 | 534 |
| GC | pullback | 0.064 | 0.064 | -0.194 | 0.356 | 505 |
| GC | exhaustion | 0.187 | 0.774 | -2.170 | 4.131 | 445 |
| GC | quiet_breakout | -0.667 | -0.667 | -4.785 | 2.939 | 532 |

## Prespecified screen

Requires positive two-tick net return and net contrast in validation and final blocks, positive two-tick return after removing the most profitable 1% of sessions, and a positive familywise lower interval.

| product | idea | later_blocks_and_concentration_pass | familywise_interval_positive | provisional_candidate |
| --- | --- | --- | --- | --- |
| ES | pullback | False | False | False |
| ES | exhaustion | False | False | False |
| ES | quiet_breakout | False | False | False |
| NQ | pullback | False | False | False |
| NQ | exhaustion | False | False | False |
| NQ | quiet_breakout | False | False | False |
| GC | pullback | False | False | False |
| GC | exhaustion | False | False | False |
| GC | quiet_breakout | False | False | False |

## Supporting evidence

- `tables/primary_summary.csv`: chronological blocks, 1/2/4-tick cost sensitivities, delay sensitivity, lower tail, loss rates, adverse movement, cost break-even, and session concentration.
- `tables/secondary_horizons.csv`: declared one-, three-, and five-bar horizons where applicable.
- `tables/declared_subgroups.csv`: signal body/wick subgroup and 09:30–10:30 **export-clock** subgroup; export timezone is unverified.
- `tables/stop_target_bounds.csv`: stop-first and target-first bounds for bars touching both, with arbitrary chart-unit barriers.
- `events_*.parquet` and `secondary_*.parquet`: event ledgers; `extraction-audit.json`: raw and accepted counts plus incomplete-horizon exclusions.

## Interpretation limits

No exact completion timestamps, verified timezone, bid/ask, fill sequence, or intrabar event order are available. The next bar's start is only a completion proxy, and opens are chart-price references. These outputs cannot establish a sustainable executable edge. Fresh unseen exports and fill-level verification are required for that claim.

# GC- Overnight Breakout 15M — Phase 2

Run: `20261013T190208Z_phase2_gc_ob15m_v2`; protocol `2.0.0`. Baseline: `20261013T142537Z_phase1_gc_ob15m_v1`.

Phase2 preserves the unchanged Phase1 baseline and uses all accepted original breakout episodes, including censored trades. Primary inward-reclaim comparisons use one common complete-day mask. Known no-fill is zero; unknown execution remains unavailable. Protected-low results use all upper-first episodes; protected-high mirrors are explicit. Actual-entry trade performance has a different cohort anchor from original-breakout paired and occurrence results.

Protected low is the frozen overnight range low, and protected high is the frozen overnight range high. Touch, one-tick breach and completed-candle closing break are separate. Same-session rates have shorter and unequal exposure; remaining-window occurrence continues after the original leg exits. Price touches/reclaims to the breached boundary, midpoint or original boundary are diagnostics rather than target fills or financial recovery.

All standardized trades use one GC contract, unadjusted same-contract prices, 15-minute confirmed decisions and observed one-minute OHLC execution approximations. The primary assumed fees are $2.50 per contract per side plus one adverse tick per fill. Signal-close initial 1% stops reset once from actual fill only at a surviving entry candle close; passive stops initially reference the submitted executable limit. Gap fills and protective exits remain executed. There is no profit target or optimized management. Assumed costs are not the user's broker charges.

Actual account experiments separately use $10,000 initial capital, 1% start-of-day risk, 10x leverage, 5% margin and whole contracts. Two-leg allocations split risk equally without replenishment or a third attempt. Financial recovery requires actual executed legs and an original realized net loss known at the first qualifying signal. Unknown equity and fills remain unavailable; observed quantity skips do not prove missing setups were infeasible. Standardized replacement profits are not source-account returns.

Development 2018–2020 and validation 2021–2023 preceded the hashed selection. Later 2024–2025 assessment and qualified available 2026 replication followed without retuning. Published baseline years are exposed, not pristine holdouts. Four-week aligned calendar block intervals use 10,000 draws and seed230015, with one/eight-week sensitivities; four primary contrasts use 98.75% marginal intervals and three upper-first protected contrasts use 98.333333%. Mirrors and subgroups remain exploratory.

Inputs end September18,2026, so 2026 is partial. Strict range completeness, roll barriers and uncertified holiday candidates reduce support. Missing later evidence remains censored. Live mapping receipt timing, annual holiday certification, tick ordering and native TradingView replay remain unverified. Closed-P&L drawdown excludes floating account equity. Phase3 EMA/cloud management and new filter searches remain uncomputed.

Saved validation decision: `retain_baseline_no_qualifying_replacement`; selected policy: `Unavailable`.

Saved later assessment: `baseline_retained_no_primary_qualifier`.

## Primary original-breakout comparisons — net USD per accepted day

| policy | episodes | complete_pairs | missing_pairs | fills | completed | mean_difference | difference_low | difference_high | adjusted_low | adjusted_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reclaim-q000 | 880 | 863 | 17 | 647 | 645 | -162.92004634994507 | -288.24313945488154 | -50.77098070562631 | -322.92724285869576 | -24.508542455811586 |
| reclaim-q025 | 880 | 863 | 17 | 469 | 465 | -237.21900347624808 | -410.6433774922306 | -86.20760806738281 | -467.8230262228568 | -51.7091668241659 |
| reclaim-q050 | 880 | 863 | 17 | 348 | 345 | -274.21784472769747 | -472.4612587844873 | -92.47527240017232 | -528.670356746527 | -39.37486342312164 |
| reclaim-q075 | 880 | 863 | 17 | 246 | 244 | -232.27694090382792 | -396.22907366071775 | -76.04956824432347 | -440.20024841417217 | -28.389387112240673 |

Source: `tables/paired.csv`; selectors `{"family": "primary", "session": "all", "side": "combined", "year": "all"}`.

## Actual candidate entry performance — all conditions

| policy | executable_fills | completed | censored | wins | losses | breakevens | net_dollars | mean_net_dollars | profit_factor | max_drawdown_dollars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reclaim-q000 | 647 | 645 | 2 | 319 | 326 | 0 | 60445.00000000405 | 93.71317829457992 | 1.138533645031179 | 40265.00000000063 |
| reclaim-q025 | 469 | 465 | 4 | 213 | 252 | 0 | -3674.99999999542 | -7.903225806441784 | 0.9875343441538779 | 47290.00000000119 |
| reclaim-q050 | 348 | 345 | 3 | 156 | 189 | 0 | -35604.99999999626 | -103.20289855071381 | 0.8223170396985975 | 44749.999999996515 |
| reclaim-q075 | 246 | 244 | 2 | 117 | 127 | 0 | 590.0000000031523 | 2.4180327868981615 | 1.00479772311448 | 40039.99999999843 |
| passive-q025 | 629 | 625 | 4 | 303 | 322 | 0 | 41825.00000000488 | 66.92000000000782 | 1.1034145979626266 | 57965.0000000014 |
| passive-q050 | 528 | 524 | 4 | 252 | 272 | 0 | -8759.999999994712 | -16.717557251898302 | 0.971993094187624 | 45984.999999999796 |
| passive-q075 | 390 | 388 | 2 | 191 | 197 | 0 | 6550.000000003087 | 16.881443298977008 | 1.0300852031325505 | 35269.99999999653 |
| protected-touch-hold | 11 | 11 | 0 | 6 | 5 | 0 | 2145.0000000002046 | 195.00000000001862 | 1.7539543057997373 | 1709.9999999999545 |
| protected-failed-break-reclaim | 227 | 226 | 1 | 105 | 121 | 0 | -15849.99999999705 | -70.1327433628188 | 0.8479543383375965 | 20904.999999999032 |
| protected-reversal | 246 | 245 | 1 | 120 | 125 | 0 | 775.0000000026412 | 3.1632653061332143 | 1.0068599247621384 | 18939.999999999043 |

Source: `tables/trade-cohorts.csv`; selectors `{"session": "all", "side": "combined", "year": "all"}`.

## Protected boundary occurrence — upper-first

| horizon | event | episodes | known_events | known_denominator | unknown | rate | lower_bound | upper_bound | mean_exposure_minutes | mean_elapsed_minutes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_session | close_break | 443 | 18 | 440 | 3 | 0.04090909090909091 | 0.040632054176072234 | 0.04740406320541761 | 171.1331828442438 | 221.66666666666666 |
| original_session | one_tick_breach | 443 | 27 | 440 | 3 | 0.06136363636363636 | 0.060948081264108354 | 0.06772009029345373 | 171.1331828442438 | 198.7037037037037 |
| original_session | reclaim | 443 | 13 | 440 | 3 | 0.029545454545454545 | 0.029345372460496615 | 0.03611738148984198 | 171.1331828442438 | 179.3846153846154 |
| original_session | touch | 443 | 27 | 440 | 3 | 0.06136363636363636 | 0.060948081264108354 | 0.06772009029345373 | 171.1331828442438 | 198.62962962962962 |
| remaining_broker_window | close_break | 443 | 113 | 442 | 1 | 0.25565610859728505 | 0.255079006772009 | 0.25733634311512416 | 615.8510158013544 | 376.287037037037 |
| remaining_broker_window | one_tick_breach | 443 | 132 | 442 | 1 | 0.2986425339366516 | 0.2979683972911964 | 0.3002257336343115 | 615.8510158013544 | 354.2204724409449 |
| remaining_broker_window | reclaim | 443 | 113 | 440 | 3 | 0.25681818181818183 | 0.255079006772009 | 0.2618510158013544 | 615.8510158013544 | 390.90909090909093 |
| remaining_broker_window | touch | 443 | 136 | 442 | 1 | 0.3076923076923077 | 0.30699774266365687 | 0.309255079006772 | 615.8510158013544 | 351.5267175572519 |

Source: `tables/occurrence.csv`; selectors `{"session": "all", "side": "upper-first", "year": "all"}`.

## Protected exploratory replacements — upper-first

| policy | episodes | complete_pairs | missing_pairs | fills | completed | mean_difference | difference_low | difference_high | adjusted_low | adjusted_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| protected-touch-hold | 443 | 436 | 7 | 4 | 4 | -361.23853211009725 | -611.1054949664464 | -138.68072463255578 | -662.3109194302442 | -93.03359926876637 |
| protected-failed-break-reclaim | 443 | 436 | 7 | 109 | 108 | -406.4908256880758 | -667.9072493632834 | -173.56917863578857 | -726.3925211242278 | -123.91854435958487 |
| protected-reversal | 443 | 436 | 7 | 107 | 106 | -371.9954128440395 | -624.3286187909371 | -136.83514335987587 | -684.6613310066012 | -83.02990167148299 |

Source: `tables/paired.csv`; selectors `{"family": "protected", "session": "all", "side": "upper-first", "year": "all"}`.

## Protected boundary occurrence — lower-first

| horizon | event | episodes | known_events | known_denominator | unknown | rate | lower_bound | upper_bound | mean_exposure_minutes | mean_elapsed_minutes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original_session | close_break | 437 | 18 | 429 | 8 | 0.04195804195804196 | 0.041189931350114416 | 0.059496567505720827 | 166.32494279176203 | 227.72222222222223 |
| original_session | one_tick_breach | 437 | 24 | 430 | 7 | 0.05581395348837209 | 0.05491990846681922 | 0.07093821510297482 | 166.32494279176203 | 207.2608695652174 |
| original_session | reclaim | 437 | 10 | 429 | 8 | 0.023310023310023312 | 0.02288329519450801 | 0.041189931350114416 | 166.32494279176203 | 237.1 |
| original_session | touch | 437 | 25 | 430 | 7 | 0.05813953488372093 | 0.057208237986270026 | 0.07322654462242563 | 166.32494279176203 | 205.66666666666666 |
| remaining_broker_window | close_break | 437 | 147 | 433 | 4 | 0.3394919168591224 | 0.33638443935926776 | 0.34553775743707094 | 637.1945080091533 | 392.56028368794324 |
| remaining_broker_window | one_tick_breach | 437 | 165 | 434 | 3 | 0.38018433179723504 | 0.37757437070938216 | 0.38443935926773454 | 637.1945080091533 | 363.9177215189873 |
| remaining_broker_window | reclaim | 437 | 122 | 431 | 6 | 0.28306264501160094 | 0.2791762013729977 | 0.2929061784897025 | 637.1945080091533 | 398.79661016949154 |
| remaining_broker_window | touch | 437 | 167 | 434 | 3 | 0.3847926267281106 | 0.38215102974828374 | 0.3890160183066362 | 637.1945080091533 | 362.59375 |

Source: `tables/occurrence.csv`; selectors `{"session": "all", "side": "lower-first", "year": "all"}`.

## Protected exploratory replacements — lower-first

| policy | episodes | complete_pairs | missing_pairs | fills | completed | mean_difference | difference_low | difference_high | adjusted_low | adjusted_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| protected-touch-hold | 437 | 427 | 10 | 7 | 7 | -96.95550351289005 | -384.75006011383977 | 186.57308333331875 | Unavailable | Unavailable |
| protected-failed-break-reclaim | 437 | 427 | 10 | 118 | 118 | -92.89227166276967 | -378.8079037870251 | 185.80926128363237 | Unavailable | Unavailable |
| protected-reversal | 437 | 427 | 10 | 139 | 139 | -89.18032786885902 | -392.4626349620779 | 207.4772687623482 | Unavailable | Unavailable |

Source: `tables/paired.csv`; selectors `{"family": "protected", "session": "all", "side": "lower-first", "year": "all"}`.

## Actual source-account experiments — original-breakout cohorts

| policy | mode | episodes | signals | eligible_loss | original_fills | second_fills | quantity_skips | completed_pairs | full_recovery | unknown | net_dollars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | original_only | 880 | 0 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-failed-break-reclaim | flat_only_opposite_reversal | 880 | 228 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-failed-break-reclaim | post_exit_reentry | 880 | 228 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-failed-break-reclaim | post_realized_loss_recovery | 880 | 228 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-failed-break-reclaim | replacement_only | 880 | 228 | 0 | 0 | 0 | 2 | 0 | 0 | 866 | Unavailable |
| protected-failed-break-reclaim | same_direction_concurrent_add_on | 880 | 228 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-reversal | flat_only_opposite_reversal | 880 | 249 | 0 | 0 | 0 | 17 | 0 | 0 | 866 | Unavailable |
| protected-reversal | post_exit_reentry | 880 | 249 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-reversal | post_realized_loss_recovery | 880 | 249 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-reversal | replacement_only | 880 | 249 | 0 | 0 | 0 | 2 | 0 | 0 | 866 | Unavailable |
| protected-reversal | same_direction_concurrent_add_on | 880 | 249 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-touch-hold | flat_only_opposite_reversal | 880 | 11 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-touch-hold | post_exit_reentry | 880 | 11 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-touch-hold | post_realized_loss_recovery | 880 | 11 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |
| protected-touch-hold | replacement_only | 880 | 11 | 0 | 0 | 0 | 0 | 0 | 0 | 866 | Unavailable |
| protected-touch-hold | same_direction_concurrent_add_on | 880 | 11 | 0 | 0 | 0 | 880 | 0 | 0 | 0 | 0 |

Source: `tables/account.csv`; selectors `{"session": "all", "side": "combined", "year": "all"}`.

## Prepared publication sources

- [GC- Overnight Breakout 15M — Boundary reclaim — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-boundary-reclaim-entry/publication.json)
- [GC- Overnight Breakout 15M — Boundary reclaim — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-boundary-reclaim-summary/publication.json)
- [GC- Overnight Breakout 15M — Boundary reclaim — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-boundary-reclaim-year/publication.json)
- [GC- Overnight Breakout 15M — Source account and two-leg risk](publications/gc-overnight-breakout-15m-phase2-20261013-v1-comparison-account-risk/publication.json)
- [GC- Overnight Breakout 15M — Phase 2 comparison — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-comparison-entry/publication.json)
- [GC- Overnight Breakout 15M — Phase 2 comparison — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-comparison-summary/publication.json)
- [GC- Overnight Breakout 15M — Phase 2 comparison — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-comparison-year/publication.json)
- [GC- Overnight Breakout 15M — Midpoint reclaim — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-midpoint-reclaim-entry/publication.json)
- [GC- Overnight Breakout 15M — Midpoint reclaim — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-midpoint-reclaim-summary/publication.json)
- [GC- Overnight Breakout 15M — Midpoint reclaim — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-midpoint-reclaim-year/publication.json)
- [GC- Overnight Breakout 15M — Passive limits — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-passive-limits-entry/publication.json)
- [GC- Overnight Breakout 15M — Passive limits — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-passive-limits-summary/publication.json)
- [GC- Overnight Breakout 15M — Passive limits — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-passive-limits-year/publication.json)
- [GC- Overnight Breakout 15M — Protected overnight boundary — Event sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-protected-events/publication.json)
- [GC- Overnight Breakout 15M — Protected overnight boundary — Occurrence](publications/gc-overnight-breakout-15m-phase2-20261013-v1-protected-occurrence/publication.json)
- [GC- Overnight Breakout 15M — Protected overnight boundary — Recovery and reversal trades](publications/gc-overnight-breakout-15m-phase2-20261013-v1-protected-trades/publication.json)
- [GC- Overnight Breakout 15M — Protected overnight boundary — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-protected-year/publication.json)
- [GC- Overnight Breakout 15M — 25% reclaim — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-quarter-reclaim-entry/publication.json)
- [GC- Overnight Breakout 15M — 25% reclaim — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-quarter-reclaim-summary/publication.json)
- [GC- Overnight Breakout 15M — 25% reclaim — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-quarter-reclaim-year/publication.json)
- [GC- Overnight Breakout 15M — 75% reclaim — Entry sessions](publications/gc-overnight-breakout-15m-phase2-20261013-v1-threequarter-reclaim-entry/publication.json)
- [GC- Overnight Breakout 15M — 75% reclaim — Summary](publications/gc-overnight-breakout-15m-phase2-20261013-v1-threequarter-reclaim-summary/publication.json)
- [GC- Overnight Breakout 15M — 75% reclaim — Year-wise](publications/gc-overnight-breakout-15m-phase2-20261013-v1-threequarter-reclaim-year/publication.json)

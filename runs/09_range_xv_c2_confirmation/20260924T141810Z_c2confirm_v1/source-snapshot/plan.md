# C2 confirmation after the first countertrend Range XV bar

Protocol frozen 2026-09-24T13:56:47Z, before this study extracts outcomes. Study 08's completed report motivates the question but is not an event input. The only bar-event input is the seven enhanced files in the pinned 2019-11-01–2026-09-24 Range XV snapshot. Source files are retained for identity and trace checks. Charts are analyzed separately: ES 4/5/6, GC 6/10, NQ 10/20. Settings from one product are correlated transformations of trades.

## Question and decisions

Does a C2 candle that follows the first countertrend C1 identify a more persistent two-bar state than an ordinary same-chart, same-direction two-bar run observed at the same session window? What does waiting for C2 give up in signal frequency and chart-price movement per original C1 opportunity?

Within one inferred 18:00 New York session, direction is sign(close−open) after rounding prices to integer exchange ticks. A doji breaks a run and is neither continuation nor resumption. The prior trend is an uninterrupted run of completed non-doji bars in one direction. C1 is the first opposite non-doji bar; C2–C4 are its next physical bars. No run or outcome crosses a session/export boundary.

The **main C1 population** requires a preceding run of at least three bars; retain 3–4, 5–7, and 8+ as descriptive bins. The **C2-confirmed candidate** additionally requires C2 in C1's direction. The C2 decision time is C2's next-bar-start completion proxy. The primary outcome is `P(C3 and C4 both close in C1's direction | C2 confirmed)`, excluding C1 and C2 from those two future bars. Also report P(C3 follows), P(C4 follows | C3 followed), the C2 failure/doji branches, and three chronological periods.

An **ordinary two-bar baseline** is any adjacent same-direction non-doji pair B1/B2 in the same session, with a strictly completed B1 and B2, whose B2 is not a main C2-confirmed candidate. Its two future bars B3/B4 have the identical completion requirements. Match candidate to ordinary baseline within product, RXV setting, direction, and the decision-time session window. This contrast is descriptive, not causal: ordinary pairs include interior runs and reversals after shorter prior runs. Save session-cluster intervals for both rates and their paired-session difference.

## Common opportunity set and price proxies

For an apples-to-apples C1 decision comparison, require strictly completed C1, C2, C3, and C4 within the same inferred session. A C1 opportunity exists regardless of whether C2 confirms. The immediate policy observes C1 and has a two-future-bar directional success if C2 and C3 follow. The wait policy observes C2, acts only if it confirms, and has a two-future-bar success if C3 and C4 follow. Report confirmation frequency, success per **original C1 opportunity**, and success per confirmed decision separately. No-confirmation opportunities remain in the denominator and contribute zero to the wait policy's per-opportunity chart-price proxy.

For a descriptive price-path comparison, use unadjusted chart opens: immediate reference entry C2 open and exit C4 open; wait reference entry C3 open and exit C5 open, where the latter is available from C4's strict completion proxy. Signed two-bar movement is in exchange ticks in C1's direction. Maximum adverse excursion uses lows/highs of the corresponding two future bars relative to its reference entry, clipped at zero. Save mean, median, 5th percentile signed ticks, median and 90th percentile adverse ticks, and event/session counts. Wait's per-original-opportunity mean includes zero for no confirmation. These are chart-price descriptions, not executable returns, fills, or profitability. Do not infer stop/target ordering.

## Timing, session, and larger-chart separation

Only `next_bar_start_proxy` statuses count as strictly completed. Exclude equal-second or unavailable completion for C1 through C4 from main decisions/outcomes; report exclusions. The decision window uses the proxy of the bar that completes the decision: C1 for immediate, C2/B2 for confirmed/baseline. Windows are half-open New York wall time: Asia 18:00–03:00, London/pre-NY 03:00–09:30, NY morning 09:30–12:00, NY afternoon 12:00–16:00, transition 16:00–18:00. Enhanced timestamps were already normalized from an inferred export clock; do not convert again. Session labels depend on the unverified ATAS timezone assumption.

Analyze one-bar prior runs only as a **separate secondary snapback context**. For ES 4→5, ES 5→6, GC 6→10, and NQ 10→20, call a one-bar C1/C2 pair aligned only if the latest larger bar's strict completion proxy is strictly before C1's proxy and its direction matches C1. Exclude equal-second larger-completion ties from this secondary estimate; report a tie sensitivity. A later larger bar must never be attached to C1. Charts without a larger partner have no snapback estimate.

## Exclusions, inference, and decision rule

Use the same five documented GC exclusions as study 08: 2026-01-28, 02-04, 02-20, 03-19, and 04-02. Reinclude them only in a sensitivity. Do not fill absent dates or missing bars. Report input hashes, bar/status/session audit, source-row traces, denominator exclusions, and price-window censoring.

For each probability record numerator, eligible denominator, distinct session dates, events/date, and a 95% session-cluster sandwich interval. Matched differences use the joint session score. Primary family: 7 charts × 2 directions × 5 decision windows = 70 candidate-minus-ordinary two-more contrasts, with Bonferroni two-sided 0.05/70 intervals. A positive headline needs ≥300 candidates on ≥100 dates and ≥2 candidates/date, its adjusted lower bound above zero, and positive period differences in each of 2019–2021, 2022–2023, and 2024–2026 with ≥30 candidate dates per period. These historical periods were previously inspected; none is pristine out-of-sample evidence. Bin, snapback, and price-path views are descriptive. A fresh later export is required to validate a selected rule.

Focused tests must cover C1/C2 counting, dojis, session and daylight-saving boundaries, same-second statuses, strict no-look-ahead larger joins, ordinary baseline exclusion, common opportunities, signed price movement/MAE, and censoring. Reconcile real events to source rows; derive report text from saved numerical tables; seal a unique local run with code/environment/input/artifact identities. No web publication is authorized by this study.

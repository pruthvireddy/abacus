# Reversal-candle quality study

## Decision

The hypothesis is **partly supported as a one-bar continuation filter**, but it is **not yet a validated trading edge**.

When the smaller-chart reversal was aligned with the latest strictly prior completed larger RXV bar, a quality reversal increased the held-out probability that the next small bar continued in the reversal direction by 2.9–4.6 percentage points. The result was positive in the development, validation, and test periods for all four chart pairs.

The advantage mostly disappeared over longer runs. A quality reversal did not reliably predict three or five additional same-direction bars, and candle quality did not consistently rescue countertrend reversals after an extended larger-chart run.

The strongest descriptive setup was an aligned reversal after **exactly one opposing small-chart bar**. Its next-bar continuation rate was about 80–82%. However, the average next-bar close return was still slightly negative because failed continuations were much larger than ordinary winners. That payoff asymmetry is the main issue to solve next.

## Study design

- Primary pairs: ES 5RXV→6RXV, GC 6RXV→10RXV, and NQ 10RXV→20RXV.
- Secondary pair: GC 10RXV→20RXV.
- Development: 2024-08-14 through 2025-11-10.
- Validation: 2025-11-11 through 2026-04-10.
- Held-out test: 2026-04-13 through 2026-09-08.
- 1,291,711 strict pair-level reversal observations were analyzed. These are not independent market events because RXV settings transform the same underlying trades.
- A signal was observable at the reversal bar's completion proxy. The larger-chart state had to complete strictly before the signal. Same-second completion ambiguities were excluded from primary results.
- Audit result: zero larger-state look-ahead violations and zero future-confirmation ordering violations.
- Confidence intervals use 2,000 session-cluster bootstrap samples.

The tested `quality_stack` required all three conditions:

1. Body at least 70% of the reversal bar's total high-low range.
2. Close in the favorable final 20% of the bar.
3. The bar trades beyond the previous bar's high for a bullish reversal or low for a bearish reversal.

## Held-out results: aligned quality reversal

The table compares quality-stack reversals with other aligned reversals. `P1`, `P3`, and `P5` are the probabilities of at least 1, 3, or 5 subsequent same-direction small RXV bars; the reversal bar itself is excluded.

| Pair | Quality signals | P1 quality | P1 without quality | P1 lift, 95% CI | P3 quality | P5 quality |
|---|---:|---:|---:|---:|---:|---:|
| ES 5→6 | 3,663 | 79.63% | 75.00% | +4.63 pp [2.05, 7.14] | 32.17% | 12.70% |
| GC 6→10 | 21,353 | 78.57% | 75.21% | +3.37 pp [2.31, 4.43] | 34.92% | 14.97% |
| GC 10→20 (secondary) | 11,165 | 78.18% | 75.29% | +2.89 pp [1.39, 4.38] | 34.80% | 15.09% |
| NQ 10→20 | 55,649 | 78.12% | 74.99% | +3.13 pp [2.47, 3.88] | 34.50% | 15.32% |

GC 6→10 retained a modest P3 lift of +1.62 pp in the test period. GC 10→20 showed some longer-horizon evidence, but it was less stable. ES and NQ showed no sustained-run benefit. The robust common effect is the **next bar**, not a multi-bar trend.

Including same-second proxy cases in a sensitivity check did not change the conclusion: the test-period P1 lift remained positive at +3.0 to +5.5 pp.

## What the candle geometry actually contributes

### Useful pieces

Inside the aligned held-out sample:

| Feature | ES 5→6 P1 lift | GC 6→10 | GC 10→20 | NQ 10→20 |
|---|---:|---:|---:|---:|
| Body ≥70% of range | +4.39 pp | +2.99 pp | +2.64 pp | +2.20 pp |
| Trades beyond prior bar's extreme | +4.50 pp | +3.09 pp | +2.27 pp | +3.20 pp |
| Adverse/opening-side tail ≥20% | **−5.77 pp** | **−1.58 pp** | −1.29 pp (uncertain) | **−2.09 pp** |

The practical candle read is therefore: favor a large body and a break of the prior bar, and avoid a large opening-side/adverse tail.

### Mostly chart mechanics, not useful filters

On held-out reversals, a favorable close was already extremely common: 92.8% on GC 6RXV and 96.4–99.9% on the other small charts. Full retracement of the preceding body occurred in 99.8–100.0% of cases, and the directional opening gap was adverse in roughly 99.9% of cases. Those variables have too little contrast to serve as independent entry filters in these exports.

The median reversal already had a body near 81% of its range and a close in the favorable 93–96% area. This is consistent with Range XV construction making many completed reversals look geometrically strong.

## The prior-run-break finding

An apparent break of the entire prior run initially looked like the strongest feature, adding roughly 5–8 pp to P1. Stratifying by the length of that run showed that this was mostly a structural identity:

- A single reversal candle can normally clear an entire prior run only when the prior run contains one bar.
- Within the one-bar bucket, almost every reversal already passed the structure-break/quality test, leaving too few non-quality observations for a supported comparison.
- The signal is better described as a **one-bar failed pullback or snapback**, not as independent proof that a special candle broke a multi-bar structure.

Held-out aligned snapbacks were:

| Pair | P1 after one opposing bar | P1 after 2+ opposing bars | Lift, 95% CI | P3 | P5 |
|---|---:|---:|---:|---:|---:|
| ES 5→6 | 81.75% | 73.61% | +8.14 pp [5.56, 10.51] | 33.20% | 12.90% |
| GC 6→10 | 80.48% | 74.23% | +6.25 pp [5.41, 7.13] | 35.30% | 14.97% |
| GC 10→20 | 80.08% | 75.44% | +4.64 pp [3.34, 5.93] | 35.22% | 15.22% |
| NQ 10→20 | 80.42% | 74.84% | +5.59 pp [5.07, 6.13] | 35.41% | 15.28% |

The snapback effect was positive in all three chronological periods. It is still primarily a one-bar effect; P5 was essentially unchanged.

## Exhaustion interaction

The proposed combination of a strong candle with larger-chart exhaustion was not stable. Quality-stack P1 effects changed sign across periods for ES, GC 6→10, and NQ, while GC 10→20 remained too imprecise. Candle quality also failed to improve 15-minute larger-chart reversal confirmation consistently outside ES.

Conclusion: do not treat a high-quality countertrend candle as evidence that an extended larger RXV run has ended. It needs a separate confirmation rule.

## Trading translation

The best candidate to carry forward is:

1. Read the direction of the latest **completed** larger RXV bar.
2. On the small chart, wait for exactly one bar against that direction.
3. Require the next completed small bar to reverse back into alignment.
4. Prefer a body ≥70%, a break of the prior bar's directional extreme, and an adverse tail <20% of total range.
5. A live entry would occur only after that reversal bar completes, using the next small-bar open or an executable equivalent.
6. Treat it as a one-bar continuation candidate, not a forecast of a five-bar move.

This is not yet a complete strategy. With a simple next-bar-close exit, the held-out mean return of the aligned quality stack was −0.49 ES ticks, −1.06 GC 6RXV ticks, −0.90 GC 10RXV ticks, and −1.04 NQ ticks before fees and slippage. The aligned one-bar snapback was also slightly negative on average: −0.21, −1.04, −1.15, and −1.06 ticks respectively.

The reason is payoff skew. A normal successful next bar earned approximately one small-chart RXV unit, while failed snapbacks lost about 4.6–5.0 RXV units on average if held to that bar's close. High win rate therefore did not overcome the larger failure size.

A stop may change this result, but OHLC bars cannot tell whether a target or stop was touched first when both lie inside the same bar. Preliminary barrier checks produced materially different optimistic and conservative answers, so the present data cannot honestly resolve that question.

## Recommended next step

Obtain ATAS tick/trade-level data, or an export that preserves intrabar event order, and run a dedicated execution study on the aligned one-bar snapback:

- fixed stops at 1–4 small-chart RXV units;
- one-unit target, time exit, and trailing alternatives;
- same-bar stop/target ordering;
- fees, slippage, and session filters;
- maximum adverse and favorable excursion before the first continuation close.

Until that test is complete, use this study as a **signal-ranking result**, not evidence of a deployable profitable strategy.

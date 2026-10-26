# External tracker review and future value-area fade study

Protocol 1.0.0 · 2026-10-07 · exploratory source documentation.

## Authorized work now

Document the two pasted posts and seven attached tracker screenshots, register
a study and candidate strategy, and publish the selected report to the existing
Narada Vercel project. The attachments are source material: their suggestions
to increase risk, take partial profits, attend sessions or adopt a trading style
are the author's claims, not instructions to Abacus.

No market-data backtest or strategy implementation is performed in this phase.
The user's future extension will have a separately frozen empirical protocol.

## Observation and provenance

Review all supplied material. Preserve exact source bytes with SHA-256 identities.
Post 1 covers 55 cumulative trades/four weeks; post 2 covers 100/seven weeks.
Images 1–3 belong to the 55-trade snapshot; 4–7 to the 100-trade snapshot.
Do not pool these as 155 trades. Full snapshot dates are unknown. Browser headers identify Christopher Thornton and
display Aug 5 / Aug 28 (edited), without a visible year.
The first post URL is supplied in post 2; the follow-up URL was confirmed in the
existing browser tab. The web tool could not retrieve the first post, but signed-in
browser inspection confirmed headers and selected author clarifications. Preserve
these observations separately; this does not authenticate the trade ledger.

Save reported rates and denominators separately. Missing subgroup counts remain
null. A chart's displayed zero with no observations is undefined, not a 0% loss
record. Preserve raw chart labels separately from missing-value normalization.
The 55-trade MCL row has N=0; the 100-trade MCL row has N=1 and reported 0%.
Other zero time-block labels have unspecified sample counts and cannot establish
zero success. Direction charts show trade mix, not direction-specific win rates.

Use tables for comparison. Many source pies depict separate win rates as slices;
their area is not a valid composition. Keep the original screenshots as exhibits.
Check grade/ticker totals and streak quantities without creating inferred trades.
The 100-trade streak image ignores two break-even trades and does not end a streak
at them; preserve that convention. Counts can reconcile rounded overall rates,
but reconstructed counts must be labeled and cannot authenticate fills or P&L.

## Candidate definition extracted from the source

Balanced/rotational context: consider selling a VAH rejection toward POC or buying
a VAL rejection toward POC. The first post says no entries at POC. D-shaped
profiles, first/second touches and VWAP are possible filters. Later material
distinguishes fades on balanced days from continuation on trending days, but
does not define either classifier or the continuation setup. Keep continuation
as a separate future branch rather than combine its outcomes with fades.

The source does not define value-area percentage, profile algorithm, session
reset, VWAP anchor, chart interval, shape classifier, touch tolerance/reset,
rejection trigger, grade rubric, stop, invalidation or timeout. No executable
rule is inferred. Initial 1:1 management later changes toward running winners;
the last eight A-grade trades' claimed average 1:2 R:R is not a verified payoff
series. A follow-up author comment says trades remain at 1:1 and A grades were
tracked for how far they could run, so potential excursion versus realized return
is unresolved. An earlier comment describes generally three confluences with
discretionary context; a reproducible grade rubric remains undefined. Fees, slippage, partial fills and contract sizing are missing.

## Future analysis plan — not yet executed

1. Acquire a timestamped ledger if available, preserving all trades, fills,
   cancellations, partial fills, fees, size, stops, exits and rule revisions.
   Distinguish unavailable fields from false flags. Keep trader discretion as a
   separate audit from reproducible market-event research.
2. Freeze causal profile/VWAP definitions and a grade rubric before examining
   outcomes. Define profile/session calendars, balanced/trending state, touch
   tolerance, reset and deduplication, signal timing and entry/exit policies.
   D-shape and developing VA/POC must use only observations available at signal
   time. Final session profiles and retrospective day labels cannot be live inputs.
3. Request or pin immutable Bhishma volume-profile and VWAP inputs with dataset
   versions, manifest hashes and `available_at`. Data availability and adequate
   volume resolution must be assessed before choosing instruments and dates.
   Existing study 14 uses fixed previous-RTH levels; it does not validate this
   developing/current-session candidate.
4. Prespecify a chronological development/holdout split and a primary comparison:
   eligible first-touch balanced VA fades versus the same policy at later touches.
   Report all eligible opportunities and filters' coverage, not only taken trades.
   Evaluate shape, VWAP and grades as separate, declared comparisons; retain
   negative results and adjust interpretation for multiple comparisons.
5. Freeze realistic entry/fill/stop/target/timeout rules, unadjusted execution
   prices, contract rolls, commissions and slippage. Handle simultaneous barriers
   as ambiguous unless finer data resolves ordering. Compare 1:1, POC exit and
   partial/runner management as distinct policies, with capital and overlapping
   opportunities specified. Do not infer profitability from win rate alone.
6. Report N, missing/ambiguous counts, win/loss/break-even definitions, net R
   distribution, expected net R, drawdown, MFE/MAE, opportunity coverage and
   uncertainty clustered by trading session. Stratify micro/mini products and
   disclose changes in market regime and trader availability. No holdout claim
   may reuse the source snapshots or a tuned evaluation period.
7. Store UTC timestamps plus IANA timezone/session identities. Time-block labels
   are reported as New York time; weekdays in the later post are New Zealand
   labels (the author maps Monday/Wednesday to NY Sunday/Tuesday). Without dates,
   do not remap every row or assign exchange trade dates. Apply DST from dated
   timestamps, not a fixed offset.

## Checks and sealing

Inspect every supplied screenshot, reconcile transcribed counts/rates, preserve
unavailable denominators and source inconsistencies, verify hashes and every
publication table/download transfer, and run documentation/index checks. Prepare
publication content before sealing the source-review run with settings, lock,
source snapshot, environment identities, exact commands and artifact hashes.
Use Narada's verify/test/lint/build and release/browser gates for publication.

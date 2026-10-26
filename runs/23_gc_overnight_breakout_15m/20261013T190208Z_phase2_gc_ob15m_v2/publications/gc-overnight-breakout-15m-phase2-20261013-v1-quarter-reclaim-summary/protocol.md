# GC- Overnight Breakout 15M — frozen Phase 2 protocol

Protocol `2.0.0`, authorized October 13, 2026. Run `20261013T190208Z_phase2_gc_ob15m_v2`. This protocol and [numeric settings](config-phase2.json) are frozen before alternative-policy outcomes. The current human request authorizes implementation, testing, execution, verification, evidence, navigation, publication and production deployment on the existing Narada site. Phase 3 EMA management and new entry-filter searches remain unexecuted.

## Baseline, population and invariants

Pin completed Phase 1 run `20261013T142537Z_phase1_gc_ob15m_v1`, manifest SHA `d2f93832610ca6e6284838ce22ca9547b8c848a1b0f06a740a345df39d94c027`, its executed protocol/config/input lock, prepared source minutes/15m/calendar/coverage, all nine scenario ledgers and independent verification. Preserve its immutable publication `gc-overnight-breakout-15m-phase1-20261013-v1`. Never rewrite baseline outputs. Read prepared bytes only after exact pin verification. Any replay stages separately and must reconcile with saved Phase 1 events and results.

Use the identical GC unadjusted same-contract input dates, clock, eligibility and costs. Phase 1 has 994 causally eligible days and 880 accepted estimated fills, including 17 censored trades; keep all episodes. The 86 unknown first-fill days and 28 known no-trade days stay in the eligibility roster rather than acquiring invented directions or entry sessions. Data ends September 18, 2026, not today. Live contract-mapping receipt, annual holiday certification, native TradingView replay and tick ordering remain unverified.

GC uses a 0.1 tick, $100 per point, whole-contract minimum/step 1. Primary standardized trades use one executable contract. Fees/slip inherit $2.50/contract/side and one adverse tick/fill. Retain independent zero-cost, zero/two-tick net, high-first/low-first and source-15m OHLC sensitivities, with paired masks and differing observation scope explicit. Slippage may change reset stops, so sensitivities execute independently. Never treat assumed fees as actual broker charges.

Original b is the 15m candle containing the first Phase 1 fill. Its direction is actionable only at its scheduled close when that candle is observed complete and usable. Later actionable signals require complete candles j>b; gaps before a first setup preserve unknown status. No backdated order on b. Native standing orders and the inherited causal-quality overlay remain distinct from the indicator fallback. Initial percentage stops are tick-rounded from signal close (market) or submitted executable limit (passive); only surviving entry candles reset once from the actual slipped fill. Preserve same-candle stops, gap-through-stop fills, next-open evening exits, invalid R with retained dollar P&L, and contract/gap censoring. No target, trailing stop or optimized stop.

## Four primary confirmed reclaims

Freeze H/L/W/M at original breakout. Long level H−qW; short level L+qW for q=0/.25/.50/.75. Raw theoretical levels are exact rational quarter-tick thresholds; confirmed close comparisons do not silently round them. Skip original trade. First later candle j closes inward (strict at q0, inclusive for q>0), then a separate k>j closes strictly outward. Submit at k close and fill the next scheduled eligible open in the original broker day/window. First setup only, at most one replacement. Expire at cutoff; opposite-boundary contact does not cancel the waiting percentage-stop rule. Missing expected fill prices are unknown, not no-fill zero.

## Exploratory passive limits

For q=.25/.50/.75 activate after complete b close. Preserve the raw level; round the executable submitted limit conservatively inward (long floor/short ceiling to 0.1), symmetrically before outcomes. Require one actual tick of intrabar trade-through; inclusive touch-only is separate. Skip a level already reached in the known post-original-fill path through b close, never using overnight construction or prefill visits. Ambiguous pre-submission chronology is unknown. Retain favorable opening gap fills even through their attached stop. No hindsight submission or pooled interpretation with confirmed reclaims.

## Protected overnight boundary occurrence and recovery

Protected low is L after upper-first; protected high is H after lower-first. It is never a swing level, guarantee or necessarily an active baseline stop. Observe from the original fill through cutoff, including after baseline exit. Exclude price paths before that fill. Record separate touch, one-tick breach, close-confirmed break and later separate-candle reclaim. Preserve same-minute first-side uncertainty and high-/low-first bounds.

Two horizons: original New York session instance (Asia crosses midnight; Outside ends at the next named session) and remaining broker window. Price event timestamps are before the endpoint. Close confirmations exactly at the New York session end belong to the next session and are excluded from horizon A. A completed candle exactly at broker cutoff can supply final descriptive confirmation when cutoff precedes the session end; no new order fills at cutoff. Record event occurrence time/bounds and confirmation availability separately.

Fully observed no-event windows are false; incomplete unresolved exposure is null. A known event survives later censoring. First observed events after an uncertain prefix are not claimed to be exact first events. Record repeated contacts, elapsed time, scheduled and observed exposure, baseline open/flat/loss-known/unknown status, actual event cohorts and transitions. Raw rates have unequal exposure and are not equal-duration probabilities.

After the first protected breach, retain price touches and separate confirmed reclaims to breached boundary/midpoint/original boundary (L/M/H for upper-first, H/M/L mirror). Keep cutoff/censoring and competing-order uncertainty. These are diagnostics, not executable targets; pre-entry contacts cannot be trade successes.

## Three exploratory protected replacement policies

All use later complete candles, first setup only, next eligible opening, 1% initial signal-close stop, inherited reset/exit/costs and no optimized management.

1. Touch/hold: touch opposite boundary, close back inside, and no one-tick breach since original fill through signal close; continuation in original direction.
2. Failed-break/reclaim: first qualifying later candle breaches by one tick; arm at that close; a separate later close returns strictly inside. Record earlier breaches before arming; do not choose the best later sweep.
3. Confirmed opposite reversal: first later close strictly beyond opposite boundary, then next-open entry opposite original direction.

Use all upper-first episodes for protected-low policy coverage and comparison, not only retrospective touch/breach subsets. Mirror lower-first separately. These policies form a distinct exploratory family; none is promoted as a validated filter.

## Actual account and two-leg financial recovery

Freeze inherited capital $10,000, 1% start-of-day equity risk, 10x leverage, 5% margin, whole GC step/minimum 1. Original-only/replacement-only allocate full budget; original plus one later leg allocates 50/50 without replenishing spent risk or a third attempt. Apply primary fees/slip. Use the validation-selected primary rule if one qualifies and the three prespecified protected rules, without choosing a protected winner after outcomes.

Separate same-direction concurrent add-on, flat post-exit re-entry, flat post-realized-net-loss recovery and flat opposite reversal. Sum concurrent notional/margin; opposite-direction signals while original remains open are skipped, never automatically hedged or closed/reversed. Ineligible first signal is skipped without a later attempt. Original loss must be realized and known at that signal. Full financial recovery means combined actual executed leg net P&L>=0; partial improvement, no improvement and further loss have distinct counts, recovery amounts/time and eligible-loss/signal/fill/completed-pair denominators. If whole-contract quantities are infeasible, faithfully report skips, zero actual trades and unavailable recovery rates. Standardized one-contract replacement profits are not source-account returns. Synthetic accounting tests must verify genuinely executed two-leg examples even if retained-history account support is zero.

## Comparisons, chronology and intervals

Primary metric is alternative minus unchanged baseline net dollars per original accepted breakout day. Known no-fill is zero; unknown/censored is null. Four-primary common mask includes baseline and all four; protected-family mask includes baseline and all three, with upper-first simultaneous scope and separate mirror. Show individual observed-pair sensitivities, rosters, missingness and retrospective contact subsets without applying future filters.

Calculate development 2018–20 and validation 2021–23 first. Save and hash a selection receipt before opening 2024–25/qualified 2026 alternatives. Select at most one primary with positive validation mean paired difference, >=100 completed validation fills in >=2 years; maximize that mean, ties prefer shallower q. Otherwise retain baseline. Later assessment requires positive net expectancy, positive paired 95% lower bound and >=100 completed fills across both later years; report failures/inconclusive results without retuning. Previously published baseline years are exposed, not pristine holdouts.

Aligned calendar-week block resampling uses 10,000 draws, seed230015, four-week primary and one/eight-week sensitivities. Preserve calendar spacing, joint policy draws, complete masks and no-fill zeros. Report pointwise95%, four-primary Bonferroni98.75%, and three upper-first protected marginal98.333333% intervals. Mirrors/subgroups do not silently expand those simultaneous families. Keep negative results visible, and do not rank on filled-only win rates.

## Saved results, visual guides and publication

Report funnels (opportunity/arm/signal/fill/completion), actual-entry trade metrics, original-breakout paired cohorts, actual boundary-event cohorts, transitions, annual within-year drawdown, hour/weekday support, entry delay/price improvement, missed baseline winners/avoided losses, recovery distinctions and unknown/ambiguous counts. Undefined ratios/R stay null. Sessions are NY Asia[20,02), London[02,09), New York[09:30,16), Outside rest, with DST and actual post-midnight calendar years. Entire trade belongs to actual fill cohort; no fill has no invented session.

Stage under the new run, retain frozen code/dirty revision/environment/commands/input+baseline pins/ledgers/masks/selections/exclusions/metrics/figures/tests/independent checks and hashes. Prepare each selected publication under `publications/<immutable-publication-id>/` before sealing, with publication source/manifest/source-cell map/verification/figures/CSV. Independently reconcile every displayed value and empirical example; diagrams are authored illustrative guides. Earliest completed net win/loss per policy/direction is the fixed empirical selection rule. Required visuals include annual paired differences, net P&L/drawdown, funnels, breach rates/exposure/recovery and session transitions.

Keep the same study page and Phase1 immutable report. Condition groups: Phase2 comparisons (including account/risk tab), Phase1 baseline, boundary/.25/midpoint/.75 reclaims (summary/year/session each), passive limits (summary/year/session), protected boundary (occurrence/trades/year/event sessions). Narada renders explicitly saved evidence only. Bounded generic singleton tabs and per-publication sealed-run source directories may be added with tests. Preserve all previous report bytes, catalog entries, release records and project protection. Execute full verified preview→staged-without-domain→verified promotion→anonymous public workflow on the existing project, retaining Phase1 current production as rollback.

The typed request ends mid-list at “Realized loss k”; its already explicit realized-loss-known-at-signal rule above governs. No inference adds Phase3, new filters or extra attempts.

The auxiliary first-1R price-path diagnostic uses the positive directional distance from the raw candidate level to its 1% tick-rounded stop, referenced to that level. Barriers are one such distance favorably/adversely from the first level touch; this is not executed-trade R. Summaries retain MFE/MAE in points, depth as a range fraction and the risk distance in points. Empirical known-no-fill examples use the earliest chronological completed baseline winner and loser per policy/direction when supported; the unchanged baseline leg is labeled, with no invented candidate entry.

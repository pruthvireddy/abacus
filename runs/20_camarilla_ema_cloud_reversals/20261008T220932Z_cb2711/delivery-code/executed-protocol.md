# Camarilla EMA-cloud executed protocol 0.3.0-executed.2

Frozen before historical strategy scoring, 2026-10-08. Draft 0.3.0 is preserved
byte-for-byte as protocol-draft.md inside staging and the completed run. This
document and config.json resolve its implementation details; the accepted draft
defines all remaining rules and the report-proposal.md defines the report.

The user's 2026-10-08 instruction supersedes the earlier planning-only scope and
authorizes implementation, input verification, historical scoring, reporting,
selected Narada source preparation and local preview. Hosted deployment requires
a separate instruction. No trading orders are implemented.

## Exact arithmetic repair before outcome inspection

An unsealed first scoring attempt was invalidated by a synthetic regression,
without inspecting its historical return summaries. Binary float prices can
miss mathematically exact GC pivot contacts. This execution uses rational
Camarilla fractions and recovers source fixed-point prices for contact, approach,
rearm and defended-pivot equality comparisons. EMA/ATR and normalized magnitudes
remain floating-point. This repairs implementation of zero tolerance; it changes
no signal rule, parameter, split or cost assumption. The superseded staging
locator is work/20_camarilla_ema_cloud_reversals/20261008T213540Z_2a83fb.

## Frozen resolutions and differences

- Accept all stated periods, exact fractions, main window, four EMA comparisons,
  horizons, one-position policy, 3R reference target and bounded comparisons.
  Freeze before any development, validation or final strategy outcomes. No tuning
  is required: development is a diagnostic period, not a parameter search.
- Close EMA seeds at the first actual observed close after a contract/unknown-gap
  reset. Wilder ATR seeds with the arithmetic mean of the first 14 TR values;
  first TR is high minus low. Features include observed partial buckets, never
  synthetic prices. Require 250 preceding observations and the specified 99%
  source-minute gate; 500-bar and strict 100% gates are separate diagnostics.
- Rebuild local five-minute OHLCV on fixed clock buckets. Every price, feature,
  pivot and fill in the primary branch uses the same unadjusted selected contract.
  Translate the saved adjusted five-minute bars by their saved adjustment solely
  for a complete aggregation and lineage cross-check. Mixed buckets are counted
  and excluded from that price parity check. No adjusted strategy branch is
  required when translation already proves the data aggregation invariant.
- Use the released expected-minute arithmetic for the two historical regimes
  supported by CME notices. Derive early GC session assignment from local dates,
  keeping 17:00–17:15 in that day's session. Do not modify the released calendar.
  Pin the conservative named holiday rule generator; individual annual holiday
  schedules are not independently certified. Exclude named holiday/shortened
  current and preceding weekdays. This conservative previous-weekday convention
  never substitutes an older valid day. Known holiday absences are treated as
  scheduled closures for EMA continuity; observed holiday prices still update it.
- Retained volume-lead mappings have verified contract identity/effective-session
  boundaries. Vendor documentation describes previous-day-volume ranking, but
  original mapping publication and arrival times are absent. Results therefore
  remain historical descriptive evidence and assumed-fill simulations. Add an
  exclusion of the first two mapping weekdays as a roll-timing diagnostic. A
  certified causal reconstruction would require separately approved contract
  volume and originally available mapping records; none is fabricated here.
- Source-condition degradation is a retrospective sample exclusion, distinctly
  labeled. No VWAP whole-day eligibility is inherited. The current day's future
  completeness is not an entry gate. Unknown later gaps censor paths and policy
  sessions. No-trade missing minutes cannot be distinguished from vendor loss;
  stringent quality gates describe observed high-coverage HLC, not settlement.
- For baseline and variants, consume the first technical rejection in each
  episode before filtering, including earlier electronic-session contacts. Only
  completed full approach-side candles rearm. Previous approach bar must be
  contiguous, same session/contract. Preserve all technical events and duplicate
  decisions in a private ledger. The separate ten-bar cooldown is shared by sides
  for a level and resets by trading session. It acts on technical rejections
  before EMA selection; it does not borrow the chart's filter-dependent stream.
- Policy risk is entry fill to the outward-rounded confirmation stop. Off-tick
  observed entry prices cancel the policy fill; historical GC tick exceptions
  remain in path statistics. Stops gap at the worse observed open, plus adverse
  slippage. Limits have one-tick trade-through and no favorable gap improvement;
  touch-fill is a separate sensitivity. The 16:00 exit is an observed minute open.
- Costs remain USD 10 round trip and one adverse tick as authorized assumptions,
  replacing the draft's request to wait for verified fees. Run all nine fee/tick
  scenarios and one-minute delay with independently re-evaluated barriers and
  occupancy. Secondary 2R/pivot exits, session windows, six one-change confluences,
  strict/500-bar gates, R4/S4 continuation and 0.225/0.325 controls stay exploratory.
- Run complete stop-first and target-first one-position schedules, retaining
  different downstream occupancy. Their reported envelope is over these two
  declared ordering assumptions, not a proof of extrema over every possible
  sequence of choices. Missing price paths have unbounded continuous outcomes;
  do not assign finite fabricated P&L bounds. No pyramiding or portfolio pooling.
- The common policy roster uses valid immediately prior HLC and feature quality
  at the candle completing at window start. A later incomplete signal window
  makes the session unresolved, including a day with no observed signals.
  Zero applies only to scorable eligible no-trade days. Quality-subset/session
  extensions have separately identified eligibility rosters.
- Four-week calendar blocks are consecutive non-overlapping New York Monday
  weeks clipped to each split. Sample blocks with replacement until the same
  number of blocks is drawn. Use identical 10,000 seeded draws across products,
  branches and endpoints within a split. Pointwise percentile intervals are
  95%; six primary contrasts also use 99.1667% Bonferroni intervals. Report the
  one/eight-week sensitivity. Require at least two contributing blocks for an
  interval and disclose bootstrap draws with undefined denominators. Sparse
  flags are <100 events or <30 sessions; they do not certify precision.
- Range/ATR tertiles use development-only observations. Weekly membership uses
  confirmation-close dates; include eligible zero-event weeks and event-weighted
  total rows. Path labels use confirmation-frozen ATR; exclude confirmation
  extrema, preserve shorter completed horizons, and censor at the same day's
  16:00 boundary. A 16:00 terminal-close label is separate from the trade exit.
- Daily21, official-settlement parity, VWAP gating and 100-bar overnight behavior
  require additional causal inputs or overnight policy and are recorded as
  unavailable optional branches. They are not silently implemented or selected.

All numerical tables, figures and report values must reconcile to saved ledgers.
Run focused synthetic tests before scoring, save exact code/environment/commands,
validate Narada source transfers and local preview, and seal a unique run only
after verification. Never overwrite a release, prior run or delivered Pine file.

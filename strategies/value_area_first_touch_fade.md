# First-touch value-area fade toward POC

Strategy `value_area_first_touch_fade` · Status: `proposed` · 2026-10-07.

Candidate from [study 19](../studies/19_value_area_fade_tracker/README.md): in a
balanced/rotational market, fade developing/current-session VAH toward POC on the
short side or VAL toward POC on the long side. D-shape, touch number, VWAP and a
predefined quality grade are proposed context variables. The source excludes
entries at POC and later separates continuation in trending markets.

Products reported: NQ/MNQ, ES/MES, GC/MGC and CL/MCL. Execution interval, profile
calculation, value-area percentage, session boundaries, shape/grade rubric,
VWAP anchor, entry trigger, stop and invalidation are not specified. The candidate
is not executable until these are frozen. All inputs must be available at signal
time; a final-session profile cannot classify an earlier developing setup.

## Evidence

External source-review run:
`19_value_area_fade_tracker/20261007T143300Z_tracker19`.
Read its [report](../runs/19_value_area_fade_tracker/20261007T143300Z_tracker19/report.md)
and [manifest](../runs/19_value_area_fade_tracker/20261007T143300Z_tracker19/manifest.json).
Its `tables/grades.csv` reports A/B/C N=10/15/30 with 100%/67%/63% at the first
snapshot, then N=22/35/43 with 86%/69%/60%. `tables/context.csv` reports D-shape
82%→80%, first touch 89%→78%, and VWAP 81%→67% (only the earlier VWAP N=16 is
known). These marginal cohorts overlap; no joint filter result is supplied.

The author's first post reports 40 VAH/VAL-to-POC fades out of 55 trades, without
their own outcome rate. Overall reported 71%→69% covers mixed setups and cannot
be assigned to this candidate. `tables/tickers.csv` preserves sample sizes and
the move toward minis. Both cumulative snapshots include the same initial trades.
There is no holdout, independently verified ledger or cost-adjusted payoff record.

Opposing/inconclusive evidence: falling A-grade and VWAP rates; unknown group
denominators; changing management; no direction-specific win rates; New Zealand
weekday labels; no support reported for same-type value-area alignment
(`report.md`, limitations). D-shape and touch patterns may reflect selection,
market state or trader skill rather than a transferable edge. Trending markets
may invalidate the fade premise; the source supplies no operational trend rule.

Initial 1:1 management changed toward letting winners run. The author's last-eight
A-grade 1:2 R:R claim and suggestion of partial profits are unverified. A later author comment says trades
remain 1:1 while A grades were tracked for potential extension; realized versus
hypothetical R:R remains unresolved. Micros had
reported partial-fill problems. Commissions, slippage, risk sizing and P&L were
not supplied. Win rates do not establish positive expected net returns.

## Current research decision

Retain as a candidate for future causal event and execution-policy analysis;
follow [the extension plan](../studies/19_value_area_fade_tracker/plan.md). No
Abacus trading or risk-increase recommendation is established. The author's
increased-risk suggestion remains a source claim. Independent testing needs
frozen rules, pinned data, chronological holdout and explicit costs/fills.

## Decision history

- 2026-10-07: registered as proposed from external reported evidence; source review
  and publication completed separately from future empirical validation.

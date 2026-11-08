# Phase 4 selection rulebook

Protocol 4.0.0 fixes one contextual pivot hypothesis, two simple pivot baselines,
one distance-only destination baseline and **one** new structural destination
hypothesis. The [protocol](protocol.md) and [settings](settings.json) are controlling.
No rule here is a recovered Verniman algorithm, a profitability finding or a
selector fitted from ten completed candidate maps. All ten predictions were
retained before the seven new source answers were opened after the recorded
capture gate and independent root review passed.

The [source-role ledger](source-role-ledger.json) retains all **143 original
Phase 2 occurrences unchanged** and adds the bounded seven-date review, totaling
303 occurrences and 72 canonical conditional-plan role occurrences. Canonical
plans, user recollections, closing-chart structural references and execution
annotations remain distinct. Both bullish/bearish trigger rows survive grouping;
identical branch intervals support one interpreted functional divider, while
different prices or independent source revisions remain unresolved as a single
pivot. Original labels, conditions, full orders, uncertainty and null historical
availability remain intact. October 6 has no retained dated canonical plan;
October 7 has two conflicting plans retained independently. These are training
observations throughout.

## Inputs, eligibility and explanations

Every executable choice must point back to an eligible frozen candidate ID,
original price/interval, construction/window, cutoff and input identity. Use only
confirmed information through **09:25 New York**, including the final five-minute
bar **09:20–09:25**. Freeze P, the terminal close, separately from the original
19 baseline fields. Required prior-RTH values must be finite and ordered
`YVAL <= YPOC <= YVAH`; the RTH/overnight distributions and exact cutoff must
be ready. Never repair a missing input with a source price or later observation.

The buffer is `b = max(2 ticks, row_size / 2)`, equal to two points in the frozen
ESZ2026/16-tick control. Permitted context is prior-value position, overnight POC
migration, identified parent membership and construction/horizon, confluence,
intervening structure and destination relationships. VIX/CVD remain **unmeasured**.
Post-cutoff acceptance, today's eventual RTH open, later highs/lows and subsequent
reactions cannot enter the pre-open choice.

A manual source-assisted explanation is a diagnostic statement. For example,
"a prior-value boundary would be needed" does not insert the source's boundary
into the generated map. A close numerical alternative with another family/window
remains an alternative, not proof that it generated the source mark. No exact
source window is established for the retained Phase 2 occurrences, so primary
exact-window coverage is **not estimable**, not zero percent.

## Pivot hypotheses fixed before new answers

**P0: contextual Autopivot policy on the strict Phase 3 interface.** This reuses
the pre-existing contextual policy; it introduces no fitted pivot rule. The saved
[Autopivot Levels - Daily](../indicator/pivot-README.md) remains a separate
comparator with its own latest-observed-RTH eligibility. P0 instead consumes
Phase 3's expected-prior-weekday RTH. That adapter difference must be recorded
as input eligibility, not attributed to selector quality.

| Condition | Original candidate selected | Reason and competing alternatives |
|---|---|---|
| `P < YVAL - b` | Prior-RTH YVAL | Prior-value reclaim boundary. POC or an interior overnight reference does not delimit prior value |
| `P > YVAH + b` and one unambiguous eligible overnight N1 parent contains P, with qualified lower E1 above `YVAH+b` | That parent's original lower E1 grid boundary | Hold the higher identified auction. Its node center and prior YVAH are different roles |
| Above prior value, but the E1 decision is absent/ambiguous/incomplete, or qualified-parent count exceeds eight | Labeled prior-RTH YVAH fallback | Conservative boundary fallback; no cap rank or later reaction resolves the ambiguity |
| Within/near prior value and `ONPOC < YPOC - b` | Prior-RTH YVAL | Overnight value shifted lower, rather than selecting the closest reference to P |
| Within/near prior value and `ONPOC > YPOC + b` | Prior-RTH YVAH | Overnight value shifted higher |
| Remaining within/near case | Labeled YPOC fallback | Balanced context supplies no unique directional divider |

Whole N1 region intervals include both endpoints. Overlapping competing parents,
missing border evidence and relevant cap omissions cannot silently resolve
uniqueness. Exact tolerance boundaries belong to the within/near branch.
Missing required inputs produce abstention. P0 fallback pivots remain identified
fallbacks; **both target branches abstain**. Confluence keeps every original
price and ID and never snaps or averages the pivot.

**B0: fixed prior-RTH POC.** Choose the ready original YPOC under the same cutoff
and strict coverage. This tests whether contextual branching adds anything over
a constant family choice. Missing P0-required context or profile readiness
produces the declared unavailable result rather than an older price.

**B1: nearest prior-value reference to P.** Among ready original YVAL/YPOC/YVAH,
minimize absolute distance to P; ties choose lower price, then stable ID. Both B0 and B1 require the same ready RTH/overnight profiles, ONPOC, P and exact
cutoff as P0, even though their selection formulas use fewer fields. B1 is
explicitly a simple nearest-reference baseline.
It does not infer the source's family from proximity. These eligibility and D0-spacing interpretations were clarified before
execution or fitting, without changing the frozen files. No new pivot alternative
or date-specific override is fitted. The saved Autopivot's separately defined
alternate reference is not automatically a target and is never imported as one.

## Why the previously exposed examples favor some roles over nearby alternatives

These comparisons use retained Phase 1 and native Autopivot v1 observations;
they are **not fresh Phase 4 predictions or complete Phase 3 candidate maps**.
Autopivot was verified on the same three dates under a distinct implementation.
Those dates' source labels were already exposed before this phase. The
[verification](../indicator/pivot-verification.md) and
[display update](../indicator/autopivot-display-update.md) distinguish the
three-date original primary verification from the later display/alternate update.

| Session | Source conditional divider | Retained pre-cutoff context and engineering choice | Why these alternatives remain unresolved |
|---|---|---|---|
| October 1 | Bullish `YVALH 7747`; bearish `YVAL 7747` | P=7729 is below prior YVAL 7752 by more than b=2; Autopivot selects YVAL 7752 | ON VAH 7744 is numerically nearer to7747, while ON POC 7740 and RTH POC 7772 have different roles. The conditional text favors a value-boundary explanation, but its unknown profile/window prevents identifying our 7752 with source7747 |
| October 2 | `HVE 7785` in both branches | P=7791.75 is above prior YVAH 7724+b; the unique overnight parent supplies lower E1=7788, uncertainty[7786,7790] | Prior YVAH 7724 is a materially different lower-auction boundary; ON POC 7760 is a center. The source point is three points from the E1 grid boundary and one point outside its uncertainty interval. That proximity does not establish the source parent, profile or threshold |
| October 5 | `HVE-YVAL 7767` in both branches | P=7774 is within/near prior value; ON POC 7768 < prior POC 7772-b, so Autopivot selects YVAL 7764, with a separately generated overnight lower E1 also at 7764 | ON POC 7768 is only one point from the source but is a center; YPOC 7772 is nearer to P than YVAL 7764. The compound source role motivates investigating boundary/confluence rather than nearest price, without proving that our profile supplies it |

Support is therefore **functional and qualified**: below-value reclaim, a higher
auction boundary and lower overnight value migration are explainable contexts.
The concrete counterevidence is retained: Autopivot grid/reference prices differ
from source divider points by **5, 3 and 3 points** respectively. All are outside
a one-point exact-price tolerance. For the October 2 E1 interval the descriptive
gap is one point; an interval coincidence is not exact boundary agreement.
No source-window identity follows from these numbers.

B0 and B1 are deliberately simple competing explanations, not rejected by a
training score here. The source's VIX/CVD conditions are absent from all these
feature sets. Exact source profile data, timestamped original revisions and
additional preserved training cases are still needed to distinguish a selector
mistake from a candidate-profile mismatch. There is no cleanly established
branch-level source counterexample with compatible windows; that uncertainty
cannot be turned into evidence that P0 is correct.

## Seven further training cases after the capture gate

These observations compare immutable `local-attempt3` predictions with the
bounded release13 selection. No selection was recalculated after source reveal.
Signed pivot differences are engineering price minus source price and describe
coordinates only. Every source's exact construction/window and historical
pre-open availability remain unresolved; VIX/CVD remain unmeasured.

| Session | Preserved source role and order | Saved decision versus alternatives | Implication and counterevidence |
|---|---|---|---|
| October 6 | No dated canonical plan. Closing PBT7915/7902, HVE7852/7812/7785/7768 and GAP7830 are structural references. Buy/flat arrows remain separate execution annotations. | P0 chooses ON lower E1=7856; D1 exits that parent at7864 before ONH7867.75. B0 chooses7828; B1 chooses7840. | This explains the algorithm but supplies no source pivot/ordered truth. Do not promote closing HVE7852 or arrows into a missing morning divider. |
| October 7 | `Record High`: YHOD7848 divider, bullish7868→7878→7890→7902→7915, bearish7830→7800. Independent `FOMC minutes`: HVE7852 divider, bullish7876→7893→7902, bearish7830→7800. | P0 selects YVAL7868 below value, versus B0 POC7876. D1 exits prior value at7884 then selects range extreme7897.5. | Single-pivot truth is unresolved across revisions; preserve +20/+16 branch differences, never the nearer revision alone. Preserve all **five** bullish targets of the first plan despite the cap. Conflicting contexts do not authorize relabeling a plan as October6. |
| October 8 | YVAL7827 divider; bullish YPOC-GAP7853→YVAH7859→GAP7875; bearish PBT7787→HVE7768. | P0 chooses YVAL7824 after lower ON POC; B1 agrees, B0 chooses7852. D1 exits prior value at7856, then range extrema7858.25/7884.5; D0 starts7832. | Difference−3 may involve profile construction, which remains unresolved. D1 skips the first modal/confluent destination and does not recover the source itinerary. Closing HVE7783 differs from written PBT7787. |
| October 9 | YVAH7833 divider; bullish GAP-PBT **[7875,7877]**→ATH-RTH7897; bearish GAP7822→YVAL-VAR7804. | P0 chooses ON lower E1=7836, versus B1 prior-value reference7828 and B0 POC7808. D1 starts own-parent exit7852, then7858.25/7872. | Difference+3 may be an origin/role error: an ON E1 cannot become prior VAH by proximity. Preserve the zone interval; do not choose a midpoint or reverse-engineer an anchor. |
| October 12 | YVAH7867 divider; bullish ONH7887→ATH-RTH7897→PBT7906; bearish GAP7862→YVAL7841→GAP7822. Recollection recovered after the next close. | P0 chooses prior YVAH7864 after higher ON POC; B1 agrees, B0 chooses7860. D1 bullish selects7870.5 then7887; bearish exits own auction at7840. | Same broad divider role but difference−3 and unknown source construction. Exact coordinate7887 is available and selected second while the source names it first. Availability differs from order agreement. |
| October 13 | Both branches print7850, bullish `HVE-YVAL` versus bearish `HVE-YVAH`. Bullish GAP7857→YVAH7864→PBT7906; bearish ONL7836→PBT7824→GAP7822. Header YPOC/GAP7856 differs from target7857. | P0 chooses YVAL7848 after lower ON POC; B1 agrees, B0 chooses7852. D1 exits7856 then7864/7870; bearish7836→7832→7820. | Difference−2; common price supports one functional divider but its family conflict is not compound confluence. D1 includes7864/7836, while other roles/order differ. Do not change target7857 to header7856. |
| October 14 | YLOD7835 divider; bullish GAP7857→CPI-SOC7878; bearish ONL7822→HVE7812. | P0 chooses prior YVAL7844 below value; B0/B1 agree. Generated prior-RTH low7834.5 exists, but the pivot rule excludes extrema. D1 bearish7834.5→7821.25→7812. | Difference+9 is a source-assisted **selector-role counterexample**: a close prior low exists but the frozen rule chooses value. Strict source-window identity remains unknown. D1's extra first bearish target also changes the order. |

The cases motivate auction boundaries and traversals while supplying counter-
evidence to universal value-boundary pivots or own-auction-first destinations.
GAP, CPI-SOC, ATH, exact PBT anchors, source profile arithmetic and VIX/CVD remain
missing evidence. No rule, threshold, date-specific branch or favorable revision
is adopted from these disagreements.

## Destination hypotheses fixed before fitting

Eligible destinations must already exist in the frozen candidate map: ready
VAH/VAL boundaries, prior full/RTH and overnight extrema, qualified E1 boundaries,
and supported non-identity causal P1/P2 projections. A target retains its original
exact reference price or E1 grid coordinate and uncertainty interval. A PBT with
no unique exact price is unavailable to this bounded exact-order policy.

Modal POCs, HVN centers and LVN intervals are not destination candidates here.
Unsupported GAP/ATH/intraday families and missing-anchor PBTs are excluded with
reasons. A matching ONH near a printed GAP cannot be silently called the same
construction. The complete-range midpoint reflection identity is not an external
PBT target. No first-pass anchor is reverse-engineered from a desired destination.

**D0: distance-only baseline.** For a ready pivot, choose at most three distinct
eligible prices strictly above `pivot+b` or below `pivot-b`, nearest first and
outward by price. As required by the global ordering setting, each successive
target must also be separated from the previous selection by **strictly more
than b**. This is price sorting. It supplies a baseline, not an explained
Verniman scenario sequence. A fallback pivot abstains from target branches.

**D1: structural-priority itinerary.** This is the **one new, unfitted engineering
alternative**. Require a ready nonfallback pivot, then apply the same stages on
each branch:

1. Prefer the opposite boundary of the pivot's own identified auction, when it
   lies strictly beyond the pivot by more than b: YVAL→YVAH bullish,
   YVAH→YVAL bearish, or selected lower E1→the same parent's qualified upper E1
   bullish. No corresponding boundary means skip this stage without inventing one.
2. Fill remaining slots with the nearest frozen full-session/RTH/overnight range
   extrema in that direction, each strictly beyond the last selected price by
   more than b. The reason is an observed range destination, not an inferred GAP.
3. If slots remain, use remaining eligible E1/VA boundaries or exact causal PBTs
   in that direction under the same spacing, with external-boundary/projection
   reason codes. Missing families leave a partial ladder.

Within each stage use ascending branch distance, then stable candidate ID.
Keep at most three per branch; bullish prices strictly ascend and bearish prices
strictly descend. Retain rejected/intervening alternatives, including omitted
modal/interior references, duplicate price, insufficient spacing, unavailable
family and cap reasons. Structural priority can deliberately skip a nearer
interior mark; the reason is the declared auction/range itinerary, not a claim
that later price proved that mark irrelevant.

Exact duplicate prices form a presentation group preserving every original ID,
family and window. Choose the lexicographically smallest ID for display; never
average or move its price. Distinct prices with overlapping uncertainty intervals
remain distinct alternatives. Missing required pivot input, pivot fallback or
unsupported target branch yields abstention/partial output rather than a complete
invented ladder. No branch uses post-cutoff acceptance to revise the snapshot.

**Support, counterexamples and missing evidence.** The sources motivate studying
destination relationships and persistent horizons, but saved training-map
comparisons do not validate D1 as the source algorithm. The examples supply counterevidence to treating
it as recovered source order: October 1's first bullish source destination is
YPOC-ONH 7767, whereas a prior-YVAL→prior-YVAH traversal using the retained baseline
would point first to 7776. October 5's first source destination is GAP 7783, whereas
the same retained-field traversal would point first to 7788. These are explicit
source-assisted illustrations; the full-history saved P0/D1 predictions now
retain 7776 and 7788 as actual first destinations. No source candidate was
inserted. They show why a plausible itinerary must retain its misses.
October 2's GAP 7803/7830 sequence also cannot establish the proposed parent-exit
construction without the source parent and gap origins.

The source October 1 bullish plan contains **four** ordered destinations
(7767,7786,7803,7830). The source ledger retains all four; the executable cap of
three does not shorten the observed denominator. Other sequences contain GAPs,
PBTs, or compound roles absent from supported executable inputs. D0 and D1 may
therefore abstain or produce only a partial geometrical itinerary. Neither can
claim complete source scenario reproduction from proximity alone.

## Evaluation and revision rules

The capture gate requires all seven additional expanded maps **and** current
Autopivot predictions to be retained and hashed before any new answers open.
Failure placeholders do not satisfy it. Do not rewrite prior exposure chronology
or describe any training session as an out-of-sample test.

For each selected source occurrence assess four separate questions: generated
candidate availability, supported construction/window identity, selector choice,
and scenario role/order. A missing full map is not a measured selector miss;
a ready candidate omitted by the selector is a different failure. Unknown source
windows, unsupported families, unavailable PBT anchors, fallback and abstention
remain separate states. Keep candidate-construction thresholds/windows fixed.

Use the protocol's one-point interval-gap tolerance and family/window-qualified
one-to-one assignment within branch/source class/revision strata, preserving
feasible alternatives and equal optima. Report reference/boundary price error
separately from interval gap; distinguish target-set coverage/extras from ordered
agreement, conditional-on-availability selection and end-to-end reproduction.
No score is reported without its eligible denominator, and a zero eligible
denominator is not zero-percent success.

The ledger's original source claims, manual explanations and executable
candidate features remain distinct. Reject broad parameter searches, later
reaction labels and date-specific choices. Any changed candidate or selector
policy receives a new identity and retains the first-pass results. Current
readiness and empirical outcomes belong in the separate Phase 4 verification
and training-results records; this rulebook cannot turn an ungenerated map into
selection evidence. During later verification a separate agent inadvertently
read protected hidden-answer snippets embedded in a concurrently expanded
general data guide. The ten maps and policies predate that incident; no rule
changes followed. Team-wide hidden exposure is therefore not pristine, and a
future hidden evaluation requires a fresh unexposed evaluator. This role review
uses only the gate-approved ten-date source selection.

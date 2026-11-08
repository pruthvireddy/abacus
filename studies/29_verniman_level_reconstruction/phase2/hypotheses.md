# Cross-case hypothesis register

Study 29 · Phase 2 · authorized cases: [October 1](cases/2026-10-01.md),
[October 2](cases/2026-10-02.md) and [October 5](cases/2026-10-05.md), 2026.

This register separates printed source facts, visual structure and proposed
construction. Source IDs resolve in [source-manifest.json](source-manifest.json);
the [protocol](protocol.md) and [Phase 3 specification](phase3-specification.md)
define the research boundary. The baseline comparison uses the unchanged
16-tick/70% Phase 1 snapshot, including only the 09:20–09:25 confirmed bar as its
last bar. No later price reaction is evidence for why a morning level was chosen.

The [knowledge-base definitions](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/glossary.md)
and [construction limits](../../../runs/27_verniman_method_knowledge/20261023T174000Z_review27/knowledge-base/levels.md)
remain distinct from these hypotheses. HVE means High Volume Edge; HVN/LVN mean
High/Low Volume Node; PBT means Projected Balance Target. A node region, its modal
price, its edge and a value-area boundary are different objects. A volume
histogram is not a TPO profile. The selected images show horizontal profile bars,
but do not identify their exact data source, binning, time window or full
calculation. Confidence in reading a printed label does not establish confidence
in recovering its construction.

## H1 — Some compound labels can be partly explained by observed extremes

**Source facts and support.** October 1's daily image (`B-20261001-I01`) combines
YPOC and ONH at a line whose axis badge reads 7767.75; the plan prints its
YPOC-ONH target as the integer 7767, with unknown rounding convention. The
independent overnight high is 7767.75. Its lower
YLOD-ONL reference is printed at 7705; the baseline ONL is 7705.00, prior full
session low 7705.50 and prior RTH low 7709.25. October 2's daily image
(`B-20261002-I01`) places GAP 7803 near the independent ONH 7802.75.

**Proposed explanation.** Retain extremes as candidates and compound labels as
claims of confluence. The October 1 YLOD component could refer to the full
futures session rather than the narrower RTH session.

**Competing explanations and contradiction.** Source rounding, feed differences
or a different session can explain the remaining fractions. Matching ONH does
not verify the YPOC component: the baseline completed-RTH POC is 7772, not 7767.
The October 2 GAP label does not prove that the gap was constructed from ONH.

**Confidence / discriminating evidence.** High confidence in the printed/axis
values and numerical proximity; moderate confidence in extreme confluence;
low confidence in the unidentified components. An explicit source session and
the underlying exact profile would distinguish these explanations. A verified
different overnight window or contract would contradict direct identity.

## H2 — The source's yesterday-value references are not recovered by our RTH profile

**Source facts and support.** The October 1 plan's YVAL 7747 differs from the
baseline RTH VAL 7752. October 2's YVAH 7744 and YPOC-GAP 7732 differ from its
baseline RTH VAH 7724 and POC 7688. October 5's HVE-YVAL 7767 is close to the
baseline RTH VAL 7764, but is also close to the overnight POC 7768. Nearby
alternatives therefore remain even when a level nearly matches.

**Proposed explanation.** Treat period identity and profile construction as
unresolved before interpreting the differences as discretionary selection.
Full electronic-session value, a composite profile, different feed/contract,
volume-at-price versus chart-bar allocation, or row/VA settings are competing
explanations. None was established by these three cases.

**Counterevidence.** A one-point proximity on October 5 does not explain the
44-point October 2 POC difference. Uniformly shifting all source prices also
fails to explain the contemporaneous extreme matches in H1. Relabeling our POC
as HVE would neither recover yesterday's profile nor resolve that contradiction.

**Confidence / next evidence.** High confidence that the named A0 values differ;
low confidence about the cause. A1, the declared 8-tick sensitivity, was not
executed because the separate experimental-layout browser workflow was blocked.
It supplies no evidence for or against smaller rows. Future comparisons need
fixed, explicitly declared sessions and profile inputs across all cases, not
per-day settings chosen to match labels.

If the image filename clocks are accurate, their earlier pre-open snapshots
and our 09:25 cutoff also differ in included overnight bars. That can affect a
developing overnight profile; it cannot by itself explain a supposedly completed
prior-session profile changing without a different reference definition.

## H3 — HVE is plausibly a profile-region boundary, with multiple unresolved detectors

**Source definition.** The generic sources describe the edge of a fuller-volume
region; they do not supply a threshold or segmentation algorithm.

**Visible support.** Daily and weekly images show fuller and thinner horizontal
profile regions alongside several HVE references. The recurring 7767 area is
named YPOC-ONH on the October 1 daily image, HVE 7767 on that day's closing map,
and HVE-YVAL in the October 5 plan/image. The October 2 map uses HVE 7785 as
the scenario divider; the same 7785 area persists on October 5.

**Proposed construction alternatives.** Test region-to-thin-volume transitions,
local profile shoulders, and confluence with a previously defined session
boundary as separate candidate families. Output an edge interval and its source
profile, rather than asserting every HVE is the single modal price or VA edge.

**Contradictions / competing explanations.** October 1's daily HVE-YVAH line is
only axis-estimable around 7778–7781, whereas the plan and closing map print HVE
7786. October 2's weekly map (`B-20261002-I02`) prints HVE 7804 while its daily
map prints nearby GAP 7803. These are separate source observations, not numbers
to average into a fitted edge. Revisions, different profile horizons, rounding
and manual context are all still possible.

**Confidence / falsification.** Moderate confidence in an edge/region role; low
confidence in any detector. A fixed detector must explain several regions with
one declared parameter set and preserve these counterexamples. Failure should
not be repaired with a different threshold for each day. Exact profile bins,
anchor times and the author's edge-marking convention are missing.

## H4 — Persistent references require a composite or carried-reference hypothesis

**Visible support.** PBT 7856, HVE 7842 and GAP-PBT 7830 are already visible in
the retained October 1 weekly image (`B-20261001-I02`) and persist in the
October 2 and October 5 weekly images. Lower HVE 7656, HVE 7634 and GAP 7621
also recur in these weekly views. The source's literal Weekly heading is
evidence of a broader presentation horizon.

**Proposed explanation.** A map can carry references from an earlier balance or
larger auction while current daily profiles develop. Candidate provenance should
therefore include the original anchor period, first identifiable time and
carry/invalidation policy.

**Limit and competing explanation.** A Weekly heading does not establish an
exact Sunday–Friday cumulative profile, a rolling five-session composite or a
particular start date. The marks could be manually retained from older auctions.
Their presence in retrospectively captured images with earlier session claims
does not independently prove original pre-open publication. It does undermine
an explanation that derives these repeated marks solely from October 5's later
move without accounting for their earlier depicted presence.

**Confidence / next evidence.** High confidence in repeated visible labels;
moderate confidence in carried/composite context; low confidence in exact
anchors. Additional authorized training examples and original time-stamped
anchor annotations are needed before automatic composite selection.

## H5 — Repeated GAP labels plausibly refer to older references, not today's unavailable open

**Source facts.** 7803 and 7830 appear as upper GAP references in the October 1
plan; 7830 is compounded with PBT in its weekly image. The October 2 plan keeps
7803/7830, and its lower YPOC-GAP 7732 recurs as GAP 7732 in the October 5 plan.
October 5 prints plan GAP 7783, while its chart labels the nearby area
HVE-GAP without printing that exact number next to the label.

**Proposed explanation.** Preserve dated gap-origin references separately from
the current developing profile, allowing compound roles and partial price
precision. A named destination may be a retained discontinuity rather than a
fresh current-day opening gap.

**Competing explanation / falsification.** The source glossary's opening/closing
definition does not identify the origin date, cash versus futures session,
unfilled condition or adjustment convention of these marks. Other gap meanings
or manual marks remain possible. Identifying a source gap with another origin
or a fully filled gap that is still deliberately retained would discriminate
policies. Today's actual RTH open and IB are unavailable at 09:25 and cannot be
used to explain a causal pre-open candidate.

**Confidence.** Moderate for persistence, low for a deterministic gap module;
required inputs are origin-session prices, reference convention and update rules.

## H6 — PBT needs explicit causal anchors; one formula cannot be selected from these images

**Source facts.** The selected October 1 weekly image already contains PBT 7856
and GAP-PBT 7830. October 5's daily image (`B-20261005-I01`) names a lower
PBT-ETH reference at an axis badge of 7746.75; the plan prints PBT 7746. Its
closing map (`X-2107206362547839375`) also shows PBT 7878, 7890 and 7917.
Those higher marks are outside the vertical coverage of the selected pre-open
images; lack of visibility does not prove they were absent or created later.

**Declared alternatives.** Center reflection `T = 2C − E` and one-range
extensions `T_up = 2H − L`, `T_down = 2L − H` remain separate symbolic
hypotheses. The anchor tuple must specify a balance interval, its center or
edge, profile/session identity, and when each component became identifiable.
Reflecting one complete bound around its midpoint merely returns the opposite
bound; it does not itself generate an external balancing target.

**Counterevidence / ambiguity.** No selected source supplies all the causal
anchor numbers and rule needed to calculate these PBTs uniquely. The ETH
qualifier indicates a distinct context for the lower projection, not proof of
which ETH range or formula was used. Many chosen anchor triples can fit a
printed target. Solving backwards from 7830 or from a closing colored box would
therefore fit the answer, and October 5's later box cannot explain the earlier
depicted 7856 mark on its own.

**Confidence / next evidence.** Low for a recovered formula; high that anchor
provenance is necessary. A manual-anchor, explicitly experimental projection
interface can be specified now. Automatic balance discovery, anchor selection
and a claim of Vern-equivalent PBT construction require more training evidence.

## H7 — Source scenario dividers are conditional selections, not automatic nearest-level rules

**Explicit source choices.** The three plans divide scenarios at 7747
(YVALH/YVAL discrepancy), HVE 7785 and HVE-YVAL 7767 respectively. Their text
also conditions the branches on bullish or bearish VIX/CVD. Higher and lower
references are ordered destinations within those conditional narratives.

**Proposed explanation.** A source reference may act as a divider on one date,
a location on another, and a destination in a different horizon. Preserve a
level's construction separately from its selected role and from confluence.

**Competing explanation / contradiction.** Proximity alone cannot resolve the
October 5 divider: ON POC 7768, RTH VAL 7764 and the recurring source HVE area
all compete. Source plans do not choose every visible intervening reference.
The three cases do not establish a rule ranking those alternatives, nor do they
recover VIX/CVD thresholds or a universal LIS selector. The label LIS itself
need not be printed for the plan's divider role to be visible; that functional
description is our interpretation, not an extra original label.

**Confidence / next evidence.** High for the stated branch choices, low for a
selector. Record timestamped scenario context and rejected alternatives in more
authorized training cases. Subsequent touches or profitable-looking reactions
cannot prove the initial selection logic.

## H8 — Closing annotations and source conflicts must remain separate evidence states

**Counterevidence to treating all drawings as morning inputs.** The October 1
closing map prints central HVE 7742 and a Bullish Imbalance assessment. A
revision history would be needed to establish how these relate to earlier
references. October 2's map states a balanced close with higher-high/
higher-low qualification; October 5's closing map shows higher PBTs outside the
earlier crop. These closing states are later observations, not proof of new
construction. Their consistency with a
morning narrative, when present, cannot certify availability at the cutoff.

**Source conflict.** October 1's plan contains VPOC 6691, while both selected
blog images print VPOC 7691. The mismatch and the YVALH/YVAL variation are input
quality findings. The pictures supply a competing value; they do not authorize
rewriting the canonical release. The HVE 7786 versus estimated HVE-YVAH region
likewise remains a source/horizon discrepancy.

**Confidence / falsification.** High for the literal conflicts; unresolved as to
the author's intended original value or revision sequence. A contemporaneous
revision history could distinguish typo, later change and different-reference
interpretations. Original source clocks, capture clocks and null `available_at`
must remain separate. None of these cases establishes a pristine causal target
test merely by comparing a closing image with a later capture of the daily plan.

## Extension readiness from this evidence

| Extension | What this phase supports | What remains required |
|---|---|---|
| Profile provenance and multiple explicit session/composite views | Ready to specify and engineer as an experimental inspection tool | Exact input identity, available-at timestamps, documented approximation and complete-period readiness |
| HVN/LVN regions | Design specified for a bounded engineering prototype; implementation awaits a frozen global policy, with no Vern-equivalence claim | Source profile fidelity, fixed segmentation criteria, stability/contrast tests and additional labeled training regions |
| HVE candidates | Candidate edge design conditional on an explicit validated parent-region policy | No recovered detector; bind edges to regions and evaluate one parameter set across cases before promoting it |
| PBT projection with manually declared anchors | Ready to specify deterministic arithmetic plus causal-anchor validation | Automatic anchors and a Vern-equivalent construction remain unidentified |
| Automatic composite selection, LIS/pivot selection and ordered targets | Research only | More authorized training examples, explicit choice/invalidity rules and retained alternatives |

These readiness judgments concern a future candidate-inspection tool, not a
tested trading system. No new detector or selector was implemented, no A1 result
was invented, and no profitability inference follows from these three cases.

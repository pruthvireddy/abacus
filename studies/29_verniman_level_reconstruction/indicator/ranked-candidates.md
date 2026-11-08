# Autopivot Levels - Daily — ranked potential levels

This revision adds other daily candidates to TradingView's Data Window. The
primary pivot, drawn alternate, profile construction and N1/E1 selector remain
unchanged. The ranks are an engineering display order, without learned
confidence or probabilities. No target labels were fitted and no training was run.

## Use the Data Window

In indicator Inputs → **Data Window**:

- **Show ranked candidates in Data Window** defaults on.
- **Ranked candidates to show** defaults to 5, configurable from 1 through 8.
- **Show candidate source details** defaults off.

Open TradingView's Data Window and place the crosshair on a bar whose confirmed
close is at or after that day's 09:25 cutoff. The terminal bar opens at 09:20 and
qualifies only when it closes at 09:25; the Data Window may label a bar by its
opening time. `Potential #1 price` through the selected limit show that day's
frozen alternatives. Historical bars retain their own day's values.
Before confirmation of the 09:20–09:25 terminal bar, or when required inputs are
unavailable, ranked values remain `na`. Empty slots remain `na` rather than zero
or a previous day's value; TradingView may render this as `∅`.

Full source names are available in the main pivot label's tooltip and the optional
diagnostic table. The tooltip lists rank, original price and all source identities
at that price. It does not move or average a level. Chart labels and the hidden-by-
default diagnostic table retain their existing display controls.

## Candidate pool and fixed order

At the same 09:25 America/New_York confirmation used for the pivot, collect:

1. Previous completed RTH YVAL, YPOC and YVAH.
2. Frozen overnight-prefix POC.
3. Qualified lower and upper E1 boundaries from retained overnight N1 parents
   whose regions are not flagged as overlapping.

Exclude every candidate whose price equals the selected primary pivot. Combine
exactly equal remaining prices into one rank while preserving all profile,
family and parent identities. Nearby unequal prices remain separate; no snapping
or averaging is introduced. Domain-truncated or otherwise unqualified E1 sides
are not eligible. This uses the existing overnight window and retained N1 cap;
there is no discretionary composite or later-session input.

Sort all eligible source candidates by these deterministic keys:

1. The existing alternate/fallback price first, when distinct and present.
2. Absolute distance from the frozen terminal close P, smallest first.
3. Source-family code, ascending.
4. Parent prominence, descending.
5. Original price, ascending.
6. N1 representative parent key, ascending.

A shared price uses the first identity under this same comparator as its
representative and retains every identity in its source list. The first visible
rank may therefore be farther from P than the next rank because the already
selected alternate has explicit priority. This ranking neither selects a second
primary pivot nor changes the existing alternate-selection policy.

The Data Window also reports the total number of other distinct potential
prices, known candidates beyond the display limit, N1 regions omitted by their
cap, and overlapping N1 parents excluded. A display limit is distinct from
missing candidate-generation evidence; neither counter establishes that the
candidate set is exhaustive.

## Optional source details

TradingView's numeric Data Window fields use these codes:

| Code | Representative source |
|---:|---|
|1|Previous RTH YVAL|
|2|Previous RTH YPOC|
|3|Previous RTH YVAH|
|4|Overnight POC|
|5|Overnight lower E1|
|6|Overnight upper E1|

For an E1 source, the parent key identifies the N1 representative row; it is
`na` for a value reference. Source flags preserve all source families at a shared
price: YVAL 1, YPOC 2, YVAH 4, ONPOC 8, lower E1 16, upper E1 32. Add the flags for
families sharing that price; for example 3 means YVAL and YPOC. Full profile and
parent names remain readable in the tooltip, including distinct parents from
the same family that a numeric family flag alone cannot distinguish.

Source details and unused rank slots are controlled by the Inputs options.
They add no chart lines. All price, identity, rank and completeness fields freeze
at the cutoff and reset for the next trading day. Post-cutoff acceptance remains
a separate changing status.

## Verification record

The focused synthetic suites passed **138 tests**: 36 Phase 1, 59 original pivot,
21 alternate-reference and 22 ranked-candidate tests. These execute translated
models and source checks; native Pine compilation and behavior are separate.

For the authorized ESZ2026 five-minute ETH configuration, the retained native
Data Window captures match the independent calculations from the same retained
TradingView bars. Values at 09:25 and after advancing to 10:05 were equal:

| Date | Primary | Alternate | Potential prices #1–#5 | Total other prices / beyond limit |
|---|---:|---:|---|---|
|2026-10-01|7752|7772|7772, 7728, 7740, 7744, 7776|5/0|
|2026-10-02|7788|7724|7724, 7796, 7764, 7760, 7752|9/4|
|2026-10-05|7764|7772|7772, 7776, 7768, 7788, na|4/0|

All 17 visible indicator fields in each cutoff/10:05 pair were unchanged,
including the primary, alternate, five displayed ranks, completeness counts and
frozen selection inputs. All three dates had zero capped N1 omissions and zero
overlapping parents excluded. Oct 5's fifth slot remained unavailable at both
times. Hidden source-detail fields are outside this six-capture price comparison.
This is a same-feed calculation and timing check, not an independent provider
comparison or validation against Verniman's proprietary target answers.

The first native compilation failed because Pine has no `array.swap`. Exchanging
the two references with `array.get`/`array.set` preserved the comparator and fixed
that compiler issue. A later reload exposed a display-visibility regression.
The rank/detail plots now disable per-plot Style editing so visibility follows
the Inputs controls. Revision 6 compiled and saved privately. After layout save
and reload, all five rank fields were present and the reopened account source
matched the local file exactly (LF-normalized). The final revision reproduced
October 1's cutoff values and passed the eight-slot/source-detail and visibility
switch checks. The complete three-date cutoff/10:05 comparison above was run on
revision 5; revision 6 changes only the 36 new plots' `editable=false` arguments.
Their calculation expressions and all selection code are byte-identical.

On October 1, optional source codes were 2, 5, 4, 6, 3; E1 parent keys were 1935
for ranks 2 and 4, with the other keys unavailable. Family flags were 2, 16, 8,
32, 4. With eight slots requested, slots 6–8 were unavailable. Turning rank
visibility off removed the rank/detail fields and left primary/alternate values
unchanged; the saved final state restores ranks on, count 5, details off and
the diagnostic table off. The final chart is left on the authorized October 1
Replay example with Data Window open.

[Current Pine source](verniman_pivot_levels.pine), SHA-256
`422aad307f2eb02a84a25083c1289759c794de745a914508ab228153c4bb64b9`.

New evidence is retained under
`work/29_verniman_level_reconstruction/20261031T014755Z_autopivot_ranked_candidates/`
relative to the Abacus root. It includes the frozen ranking contract, before/after
sources, focused test outcomes, retained-bar expectations, native cutoff/advanced
captures, comparison results, failures and display-correction evidence. Existing
Phase 1/2 and prior indicator verification records remain unchanged.

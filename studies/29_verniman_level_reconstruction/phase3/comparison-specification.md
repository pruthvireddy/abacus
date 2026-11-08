# Phase 3 training comparison contract

Protocol 3.0.0 uses the frozen [protocol](protocol.md) and
[settings](settings.json). This document explains reporting and eligibility;
it does not change the detector, tolerance, input policy or reveal gate.
Candidate generation is an engineering hypothesis. A nearby source annotation
does not establish that the candidate reproduces Vern's construction.

The local [matcher](matching.py) consumes explicitly supplied saved references;
its [synthetic tests](../tests/test_phase3_matching.py) execute no source or
market-data reads. Callers normalize exact identities explicitly and use
`window_id=None` for unknown periods. It returns descriptive alternatives for
unidentified windows without adding them to primary coverage. Supplying a
failure or baseline-only map requires `candidate_map_ready=False`.

## Reveal and retention gate

Retain actual expanded maps for **all seven** additional dates—October 6, 7,
8, 9, 12, 13 and 14, 2026—before opening any of their target sources. Retain
the input, code and settings identities, complete local calculation ledger,
baseline values, profile memberships, readiness and browser status with each
map. An unavailable map or a failure record does not satisfy this gate.
Keep those answers closed when data or native access prevents the first pass.
October 1, 2 and 5 are already exposed training examples, never holdouts.

Source access, if the gate later passes, uses exact dates through the pinned
public loader and exact intake filenames. Preserve selected source revisions,
original locators/hashes and every null historical availability value. Retained
pixels and a fresh browser visit are different inspection methods. Development
October 15–20 and hidden-test October 21–27 answers remain excluded.

## Observation units and suitability

An observation is an identified source occurrence, with source revision, date,
source class, original label, family roles, price interval, reading basis,
contract evidence, reference period and timing qualification. Keep these source
classes separate:

- Named daily-plan references and their stated conditional roles.
- Structural chart labels on a selected map, with its visible price domain.
- Later intraday or closing annotations and their later-presence evidence.

Execution arrows, P&L, floating current-bar readouts, unnamed histogram lines
and range-width numbers are not source level-selection labels. Absence from a
crop is not evidence that a level did not exist. An unresolved historical clock
does not become a certified pre-open answer because a reconstruction is ready.

The source's family, window and timing suitability are separate fields. A
readable price may have an unidentified construction or window. Preserve
literal conflicts such as 6691 versus 7691 and 7746 versus 7746.75. Do not repair,
average, merge or pick the version closest to a generated candidate.

## Family and window qualification

Primary coverage requires a readable finite interval, compatible contract and
price coordinates, a declared family, and a known compatible reference window.
An exact window includes the source session/member identity and its measurement
cutoff where the distribution develops. A generic `Weekly` heading does not
identify the current-week prefix, previous completed week or fixed three-RTH
composite. The word `yesterday` alone does not resolve RTH versus full ETH.

| Source role | Compatible generated role, when its window is established | Prohibited substitution |
|---|---|---|
| HVN / LVN | Same-family region on the identified distribution | Single POC as all nodes; domain endpoint as an LVN |
| HVE | E1 boundary with identified HVN parent on that distribution | POC, VAH/VAL or node center renamed HVE |
| PBT | Separately named eligible P1 or P2 projection with declared anchors | Back-solved anchors, missing anchors or midpoint identity counted as an external target |
| YVAH / YPOC / YVAL | Corresponding prior-profile baseline role under a known session convention | Nearest weekly or overnight value silently treated as yesterday's value |
| ONH / ONL | Corresponding overnight extreme under the same clock/cutoff | GAP, current RTH extreme or a different overnight prefix |
| YHOD / YLOD / prior close | Corresponding qualified period extreme/last trade | Unknown RTH/full-session convention or GAP treated as settlement |
| GAP / ATH-RTH / LOD / unresolved role | Explicit unsupported-family or unavailable-at-cutoff status unless independently implemented | HVE/PBT/extreme assigned solely by proximity |

Unknown windows and unimplemented source families remain in the readable-source
denominator but are excluded from the primary eligible denominator, with a
reason. Retain their family-appropriate descriptive alternatives separately.
Do not call them detector misses or primary matches. An unmatched eligible
reference is a first-pass miss under this control; an unmatched generated
candidate is not automatically a false market level because the source map can
be selective.

For the preserved Phase 2 inventory, all 143 occurrences have unspecified or
unknown reference-period coordinates. They can support descriptive comparisons;
none currently meets the frozen exact-window rule for primary coverage. A
zero eligible denominator means **not estimable**, not zero-percent coverage.
This eligibility result is a metadata qualification, not a new pixel reading.

## Global error and one-to-one assignment

For source interval `[s0,s1]` and candidate interval `[c0,c1]`, interval gap is
`max(0, s0-c1, c0-s1)`. Exact prices use degenerate intervals. A feasible pair
requires interval gap **at most 1 ES point** and family/window compatibility.
Retain each interval's width and reading basis; a wide interval is not a
precise price match. For E1 also report its actual grid boundary and signed
source-to-boundary error, alongside the uncertainty interval.

Within each date, source class, source revision, family and compatible window
stratum, select a one-to-one assignment by maximum cardinality, then minimum
total interval gap, then lexicographic source/candidate IDs. Record all feasible
alternatives and equal-optimum ambiguities separately. A deterministic chosen
assignment does not remove scientific ambiguity. Generated candidates cannot
be counted twice within a stratum. Counts across revisions/classes are separate
observational summaries, not independent confirmations.

Keep compound labels as one original occurrence with multiple roles. Per-role
tables may assess each supported component, but an occurrence-level summary
counts that occurrence once and discloses partial versus full-role coverage.
A matching ONH component does not validate an accompanying YPOC component.
Never pool overlapping family denominators into an apparent overall success rate.

## Required reported fields

For each training date, retain source suitability and exclusions; readable and
eligible counts; matched pairs and unrounded interval gaps; ambiguous alternatives;
unmatched eligible source references; unsupported or unresolved source references;
unmatched generated candidates; complete and displayed candidate counts; cap
omissions and IDs; profile/member identities; PBT readiness or missing-anchor
reason; and native/browser evidence status. Preserve the first pass unchanged.

If expanded maps are unavailable, comparisons are **not executed**. Do not
substitute Phase 1's baseline-only evidence or synthetic distributions, and do
not report fabricated candidate counts or coverage. Future discrimination should
first seek exact source profiles, session/cutoff identities and causal anchors;
any detector revision receives a new identity and retains the original misses.

# Phase 5 artifact and entry-readiness reconciliation

This is a static identity audit for
`work/29_verniman_level_reconstruction/phase5_20261031T023320Z/`.
The [Phase 5 protocol](protocol.md), [settings](settings.json),
[input declaration](input-declaration.json) and [decision rule](decision-rule.md)
were frozen at **2026-10-31 02:33:20.130920 UTC**, before development answers.
This audit did not read development, hidden or outside-period answer material,
open a browser, or read the mutable general data guide.

## Exact retained identities

Every proposed identity matches the [Phase 4 handoff](../phase4/phase5-handoff.md).
No expected hash was silently updated.

| Item | Version or role | SHA-256 |
|---|---|---|
| [Candidate Pine](../indicator/verniman_levels_phase3_3_0_2.pine) | Candidate implementation 3.0.2; mathematics/control 3.0.0 | `034c3731f2ada4620aac9a80ca20261d0a06376bee044fa30e95529ad9e1954c` |
| [Selector Pine](../indicator/verniman_levels_phase4.pine) | Selector implementation 4.0.1; selection control/protocol 4.0.0 | `1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924` |
| [Local selector model](../src/phase4_model.py) | Unchanged translated-model implementation | `bec68316b9028cff8d43e6e9fbcef86c4e46a5be792b9df325d42753a85547c5` |
| [Candidate settings](../phase3/settings.json) | Original control 3.0.0 | `c0297d86f2a6dce33b6888a174c31d6390477dd0e12d78a46832173e0f17653a` |
| [Selector settings](../phase4/settings.json) | Original selection control 4.0.0 | `5a1cc36f7c0a2b16ee82ab9eccd285c9a897d933d2b0ad1e02a2c026e5bb5f1a` |
| [Matcher](../phase3/matching.py) | Unchanged family/window and one-to-one contract | `b595fbca570df868888dd58c8fe341ee341b69770d902319ba25ac8fd1fd90a6` |
| [Retained Autopivot source](../../../work/29_verniman_level_reconstruction/phase4_20261031T010249Z/autopivot-current-reconciliation/studies/29_verniman_level_reconstruction/indicator/verniman_pivot_levels.pine) | Immutable Phase 4 capture; private revision 5 readback | `228ce4f4cc938cfb967eed4b20df8db0711755fb2fd8d4ae2cc9be8632dd3145` |
| [Retained Autopivot model](../../../work/29_verniman_level_reconstruction/phase4_20261031T010249Z/autopivot-current-reconciliation/studies/29_verniman_level_reconstruction/src/pivot_model.py) | Corresponding immutable comparator model | `1fc67f44ea3dc6bc374a3bfcf526bfea419af8316f7eaf82cc179d01c3e466f4` |

At the entry audit, all **38** files in the final Phase 4 source snapshot matched
their recorded hashes in both retained and then-current locations. Both phases' four frozen protocol
documents also pass their byte checks. Relevant unchanged dependencies include
`phase3_model.py` (`e54ba995…`), `reference_model.py` (`712016db…`), the Phase 4
reporting runner (`9c936876…`) and source-role helper (`e1f4b7c0…`). The private
stored selector revision 1 readback normalizes to the exact selector hash above
after **CRLF-to-LF only**; the retained candidate readback is already byte-equal.
The machine-readable audit retains full dependency hashes and checks:
[artifact-reconciliation-checks.json](../../../work/29_verniman_level_reconstruction/phase5_20261031T023320Z/artifact-reconciliation-checks.json).

The mutable workspace Autopivot has the separately recorded source hash
`422aad307f2eb02a84a25083c1289759c794de745a914508ab228153c4bb64b9`.
The retained post-freeze reconciliation shows that it adds `editable=false` to
36 diagnostic plot calls, with unchanged model and selection arithmetic. It is
not substituted for the immutable capture or relabeled as the source of earlier
predictions. This task preserves the user's **Autopivot Levels - Daily** indicator
and its primary/alternate policies.

## Information-policy differences

All six predeclared configurations are **P0-D1, P0-D0, B0-D0, B0-D1, B1-D0 and
B1-D1**. The Autopivot primary and alternate remain separate pivot comparators;
the alternate is not a destination ladder.

| Convention | Phase 5 candidate/selector interface | Immutable Autopivot comparator |
|---|---|---|
| Prior RTH | Strict expected prior weekday; Friday for Monday. Missing expected input withholds it. | Latest actually observed RTH; an absent weekday and a closure are not independently distinguished. |
| Candidate scope | Five distribution families, full calculation/rejection ledgers, fixed three-RTH composite and causal PBT policy. | RTH and overnight input; overnight N1/E1 with retained-parent selection/confluence gates. |
| Parent caps | Full candidate accounting precedes presentation caps; P0 explicitly reproduces conservative comparator fallback gates. | Eight retained N1 parents; a parent omission can force a higher-auction fallback. |
| Cutoff input | Retain the completed 09:20–09:25 bar and its close P separately from the original 19 fields. | Same declared cutoff close; later acceptance is a separate display. |
| Missing families | Empty first-pass PBT anchors remain unavailable; VIX/CVD are unmeasured. | Neither alternate references nor acceptance establish missing source inputs. |

An input-policy disagreement is not a measured selector-quality difference.
The declared feed, individual unadjusted contract, five-minute ETH bars, New York
sessions, zero grid, 16-tick rows and 70% value area remain fixed. No source price
may repair a missing anchor or generated candidate.

## What earlier verification establishes

Phase 4 retained ten complete training maps and native compilation/private
readback for the exact source. Its final selector cutoff/advance/restart matrix
covers October 1, 2 and 5. Candidate family summaries, compatible-history hashes,
failures, corrections and limits remain in the earlier records. These are
prerequisites, not native verification of October 15, 16, 19 or 20.

Phase 5 must independently retain all four complete expanded maps, all six
configurations, input/producer hashes and each development date's native primary
cutoff/advance/restart evidence before its reveal gate can pass. A static hash
audit does not establish new input readiness, native execution, same-feed parity
or source-method agreement. Earlier failure records and the old study README's
historical phase scope are preserved; the latest user authorization and frozen
Phase 5 protocol govern this new work.

## Exposure and final-evaluation limits

Only metadata from the preserved exposure event was read. It records numeric
answer exposure for October 21, 22, 23 and 26 and outside-period October 28–30;
October 27 was metadata-only. No prices are reproduced here. The original hidden
period is permanently qualified in the study history. A fresh evaluator cannot
erase that exposure or make the original period pristine.

The [decision rule](decision-rule.md) requires identifiable common primary units
on at least three development dates before a strict mechanism comparison can
select a unique dominating alternative. Coordinate proximity cannot pass that
gate. If engineering passes but identifiability fails, P0-D1 may remain only an
engineering default, with **no validated configuration selected**. Unknown exact
source windows remain outside primary denominators; zero eligibility is not
estimable. The [Phase 6 eligibility design](phase6-handoff.md) proposes a separate
prospective route and authorizes no final evaluation or replacement-answer access.

Later Phase 5 maintenance of the shared check registry has its own authorized
scope and final verification. The dated entry audit is not relabeled as a
post-maintenance check, and the retained Phase 4 snapshot is never rewritten.

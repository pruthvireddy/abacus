# Phase 5 verification

Execution stage:
`work/29_verniman_level_reconstruction/phase5_20261031T023320Z/`.
The [protocol](protocol.md), [settings](settings.json),
[input declaration](input-declaration.json) and [decision rule](decision-rule.md)
were frozen at **2026-10-31 02:33:20.130920 UTC**, before development prediction
execution or answer access. Their stage receipt is `protocol-freeze.json`.

The [artifact reconciliation](artifact-reconciliation.md) verifies the proposed
candidate implementation 3.0.2/control 3.0.0, selector implementation 4.0.1/control
4.0.0 and immutable Phase 4 Autopivot comparator. Earlier phase files are pinned
in `prior-study-preservation-pins.json`; unrelated working-tree paths are retained
in `working-tree-initial.txt` without displaying protected content.

The engineering checks below have completed. Source-method outcomes and the
final configuration decision are separate from native execution and same-feed
parity. A planned action or a clicked Forward control does not establish
successful native behavior.

The new native layout is **Verniman Levels Phase 5**,
`https://www.tradingview.com/chart/0cDKxwlq/`. It was created through the normal
Create new layout action; prior layouts and saved indicators were preserved.
An earlier stale tab was recovered with a fresh tab in the same in-app browser.
Its initial loaded chart showed current neutral market data; no outside-date
Verniman answer source was opened or used. Only the four authorized development
dates may be selected in Replay.

The pre-answer exposure audit records existing training exposure, the prior
hidden October 21/22/23/26 numeric exposure and October 27 metadata-only exposure,
without reproducing protected prices. Outside-period October 28–30 snippets were
also exposed previously. This phase never claims the old holdout pristine.
No development answer has been opened before its new gate. No Phase 6 execution
or replacement-answer inspection is authorized.

## Exact native source and settings

The unchanged selector source compiled and was added at **22:35:00 New York**.
It was saved privately as **Verniman Levels Phase 5 verification 4.0.1**, revision
1, in the separate Phase 5 layout. The private library shows the save at 22:37.
A subsequent stored-revision reopen/readback matches source SHA-256
`1145834bfb240029f07342e52f98d805771ca4f2a39a646c19e80d3846794924`
after CRLF-to-LF normalization only. Indicator title remains **Verniman Levels**;
selection control is 4.0.0, selector implementation 4.0.1 and embedded candidate
implementation 3.0.2/control 3.0.0. This is a verification copy, not a new rule.
The saved layout reports **All changes saved**. The user's Autopivot and prior
layouts were not overwritten.

Actual settings were CME_MINI:ESZ2026, CME GLOBEX, individual unadjusted December
contract, standard five-minute candles, ETH, America/New_York, zero grid,
0.25 tick, 16-tick/four-point rows, 70% value area and 09:25 cutoff, with P0/D1
and empty manual anchors. The exact included bar is **09:20–09:25**, never
09:25–09:30. Source/library/settings text and hashes are retained in
`native-source-verification-final.json` and `native-evidence/`.

## Four-date native primary verification

Every date has separately captured cutoff, advanced-into-RTH and restarted
observations. Original candidate IDs, prices/intervals, reason codes, rank,
fallback and branch status remained invariant in each three-state receipt.
Each advanced chart export includes a 10:05 bar opening; its preceding completed
10:00–10:05 bar establishes advancement through at least 10:05 New York on every
date. This is observed chart evidence, not an inference from Forward-click counts.
Full native IDs and original group/originating IDs remain in the saved text;
the table summarizes the actual native observations.

| Development date | P0 pivot / reason | D1 bullish targets | D1 bearish targets | Branch status bullish / bearish | Cutoff / advance / restart |
|---|---|---|---|---|---|
| October 15 | 7748 / `P0_BELOW_VALUE_RECLAIM` | 7796, 7837.75, 7879.75 | 7741, 7728.75 | ready / partial | Equal |
| October 16 | 7796 / `P0_PRIOR_VAH_FALLBACK` | None | None | unavailable / unavailable | Equal |
| October 19 | 7760 / `P0_ON_VALUE_SHIFT_HIGHER` | 7768.5, 7803.25, 7809.5 | 7680, 7677 | ready / partial | Equal |
| October 20 | 7736 / `P0_BELOW_VALUE_RECLAIM` | 7752, 7773.25, 7780 | 7727.5, 7704.5, 7677 | ready / ready | Equal |

October 16 is a genuine observed policy fallback, with detail `ABSENT` and
`PIVOT_FALLBACK_TARGET_ABSTENTION` on both branches. It is not relabeled as a
complete ladder or missing source input. October 15/19 have partial bearish
ladders, with the third target still unavailable. Later live price changes did
not revise these decisions or their cutoff close P.

October 19's first direct pivot-cell captures selected the wrong tooltip. Their
raw captures and assembly failure remain retained. The correction used the
**actual selected pivot row in the native alternative ledger** at cutoff, after
advancement and after restart. Those text/screenshot supplements contain the
original native ID and selected reason. No ID or native value was filled from a
local prediction. Acquisition-time approximations and the later explicit capture
times remain separately qualified in the per-state provenance. Parser revisions
support the additional observed row format; they do not change Pine or numerical
selection. The corrected receipts remain attributable to their actual evidence.

`native-verification/2026-10-15.json`, `2026-10-16.json`, `2026-10-19.json` and
`2026-10-20.json` bind the captured text, independently reviewed chart PNGs,
settings/source identity and three-state comparisons. Native/model namespace
strings differ; mappings preserve each original ID at its construction/window,
coordinate and reason. No byte equality of those namespaces is claimed.

## Compatible history and same-feed local parity

Each raw native export contains **3,216 rows**. The local cutoff filter retains
3,215 and excludes the one bar opening at 09:25 on every date. All 32 declared
fixed-clock coverage windows are complete: prior full, prior RTH, overnight,
current-week prefix, previous week and each of three completed-RTH composite
members per date. There are no missing/invalid bars or duplicate included
timestamps in those checks. Overlapping warm-up history is not independent data.

The local batch contains four complete expanded maps, **20 ready distribution
profiles**, all **76 original baseline fields**, cutoff close P, all six declared
configurations, full candidate/rejection ledgers, composite lineage and PBT
eligibility. All observed presentation-cap omissions are zero. First-pass manual
anchors are empty and PBT outputs remain unavailable; no answer price supplies
an anchor. Input bytes, producer snapshots and command receipts are retained in
`market-inputs.json`, `producer-1.json`, `input-coverage-1.json` and
`predictions-1/prediction-batch.json`.

The complete batch was recorded at **02:54:54.971937 UTC**, with each map captured
between 02:54:54.685910 and 02:54:54.909844 UTC. Its original fields explicitly
say reveal/native/source-method approval was not yet established by that local
producer. Those historical fields remain unchanged; the later native and reveal
receipts establish their own scope.

The explicit parity audit `native-local-parity-1.json` passed all four dates:
P0/D1 numerical selections, reasons, fallback and branch status agree with the
local saved translations, and native three-state decisions remain invariant.
This audit checks saved actual observations and byte integrity; it does not
itself execute Pine, independently OCR the chart, validate every internal
candidate on every profile, or establish agreement with Verniman's sources.
The native source/PNG/text records establish the separate execution scope.
Maximum 6,000-row runtime and native execution of every baseline combination
are not claimed.

## Pre-answer decisions and reveal chronology

The pure [decision assessor](assess_decision.py) and
[strict-unit distiller](distill_decision.py) were implemented and tested before
answer access. Forty synthetic tests passed with zero skips. They cover common
units/dates/denominators, unknown windows and conditions, ties and competing
dominators, abstention, unsupported geometry ranking, generation failures,
compound/duplicate counts, preserved destinations beyond cap, saved-input
integrity and actual E1-boundary agreement distinct from uncertainty overlap.
The real test output and exact pre-answer code/clarification hashes are retained
in `decision-tests-pre-answer.log` and `decision-distillation-pre-answer.json`.
These tests neither execute Pine nor read real source answers.

The machine gate was recorded at **02:59:18.504440 UTC**, after the complete
prediction batch and all four native three-state records. The root review at
**03:00:16.309372 UTC** approved only the exact-date source selection. The
guarded loader's gate recheck passed at 03:00:16.400617 UTC; release 13 intake
then began at **03:00:16.540139 UTC** and completed at
**03:00:22.317506 UTC**. `reveal-gate-1.json`, `root-reveal-review.json` and
`source-selection-manifest-release13.json` retain the chronology and exact
hashes. No failure placeholder or baseline-only record unlocked access.

Only October 15, 16, 19 and 20 source rows/intakes were selected. Source-role
review, saved-prediction comparisons and the final decision use those bounded
outputs. New source-method results are not implied by the engineering passes
above. Final repository test outcomes and artifact-preservation checks are
recorded separately when the complete source/report scope is ready.

## Saved source comparisons and applied decision

The [development report](development-results.md),
[assessed source ledger](source-role-ledger-assessed.json) and
[candidate-choice index](candidate-choice-ledger.json) retain all 98 source
occurrences. The original source-role input remains byte-pinned; its saved-only
comparisons use the exact four pre-reveal maps without rerunning selection.
One canonical revision exists per development date. Structural, recalled and
later/closing annotations remain separate from canonical scenario truth.

No independently supported exact source-window metadata was supplied. Common
eligible primary units and dates are therefore zero for the pivot and both
branches, against the frozen minimum of three dates per role. VIX/CVD remain
essential unmeasured conditions. Strict source-method coverage, conditional
selection and end-to-end agreement are **not estimable**, not zero percent.
All source historical availability stays null; October 20's canonical claimed
update after cutoff is retained rather than certified as pre-open availability.

The [final assessment](final-assessment.md) applies the unchanged decision rule:
**no validated configuration selected**, P0-D1 retained only as the engineering
default, and source-method final evaluation not ready. Its JSON and
`decision-assessment-1/` retain actual strict-unit exclusions, source/score pins,
pre-answer helper hashes and exact execution. Descriptive coordinate advantages
are reported separately and cannot switch the default. The original hidden
exposure history and prospective proposal remain in the
[Phase 6 handoff](phase6-handoff.md); no replacement period or Phase 6 execution
was adopted.

## Final repository checks and preservation

The final registered Study 29 check passed **471 tests, zero failures/errors and
zero skips**, including **164 Phase 5 synthetic tests**. The new orchestration,
gate, window metadata, native receipt parsing, fixed scoring/decision and
independent audit logic are covered; synthetic tests do not execute Pine or
establish source-method fidelity. An earlier 459-test pass preceded the final
12 independent-audit tests and remains retained. Final output is
`study29-checks-final-2.json` and its command log.

The independent saved-comparison audit passed **27 literal canonical roles and
384 metric checks**. It uses its own exhaustive coordinate assignment rather
than calling the study matcher or selector. It confirms the report's geometry
and denominators without turning unknown source windows into eligible matches.
`independent-source-comparison-audit-1.json` and the separate final report-review
receipt retain its exact inputs and scope. The delivery-integrity receipt checks
all 98 source facts/IDs, choice order and unchanged original ledger/maps/scores.
The independent report/assessment review passed 1,068 additional checks with no
actionable issues; `independent-audit-completion-1.json` pins both audit records,
their code and the 12 passing independent-audit tests.

Registry tests passed **35 tests**. Documentation checked **141 active guides
with zero errors**. Initial checks made before the report/manifest files existed
failed only on those absent targets; their logs remain retained, and the complete
files passed subsequent checks. The manifest was explicitly marked as a draft
while link verification ran, with that draft separately retained before the
final immutable manifest was written.

A subsequent recheck observed **concurrent, unrelated Study 27 work** expanding
the registry to 144 guides. That documentation check has three missing links in
Study 27's daily-map guide. The current registry suite runs 35 tests with two
failures: the prior 141-guide expectation and Study 27's former guide list.
These later workspace results supersede the earlier green global checks for the
current tree; no Study 29 link or owner-list failure was reported. The current
logs and `final-checks-2.json` preserve both results. This phase does not repair
or overwrite the concurrent owner's work.

The required default workspace gate is **not green**. Its documentation check
passed, then Bhishma discovered 995 tests and ran 988, with two setup errors and
zero skips: the configured continuous volume-rank roll-map file is missing, and
ES roll 1 has no point-in-time definition pair in its ten-day search window.
These are the previously recorded unrelated input prerequisites. No dataset or
historical publication was rebuilt to repair them. The gate stopped before
Sahadeva, legacy-01, legacy-02 and vwap-doctor; those four checks were **not run**.
`workspace-default.json` and its log retain the actual result.

The final freeze binds the locked environment, exact producer/scoring/decision
snapshots, complete stage inventory, maintained reporting files, and a final
preservation receipt. The receipt checks all **107 earlier Study 29 files**, all
four pre-answer protocol documents, the original four prediction maps plus batch,
and saved comparisons/original source ledger against their earlier hashes.
This is a byte-integrity check, distinct from research revalidation. Unrelated
dirty paths were preserved; no comprehensive audit of their bytes is claimed.
The first final inventory caught its own command log while that log was still
being written. Its manifest and inventory remain retained as attempt 1. The
corrected final inventory was made after that log closed and passed a complete
readback. This changes inventory bookkeeping only; no source facts, predictions,
scoring, settings or configuration decision changed.

No navigation inputs, Narada publication or app components changed in Phase 5;
index regeneration and Narada tests/build were not run. No hidden test,
replacement-answer inspection, P&L, publication or deployment was performed.

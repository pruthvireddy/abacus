# Phase 3 verification and access record

Study 29 · protocol 3.0.0 · 2026-10-30 New York. This record separates local
specification checks from native Pine/Replay and research evidence. No completed
run is sealed. Stage: `work/29_verniman_level_reconstruction/phase3_20261031T003524Z/`.

The [script](../indicator/verniman_levels_phase3.pine), [protocol](protocol.md),
[settings](settings.json), [calculation specification](calculation-specification.md)
and [ten-date status](training-results.md) define exactly what is delivered.

## Native browser result

The logged-in in-app browser opened the verified
[Phase 1 layout](https://www.tradingview.com/chart/mtK3TbRP/), showing ESZ2026,
five-minute standard candles and electronic trading hours. The browser exposed
TradingView's normal Make-copy dialog. Submitting the separate name **Verniman
Levels Phase 3** was rejected by browser security:

> The browser blocked this navigation; this was not a site-status decision or a user rejection. Browser Use is not permitted on this page.

The rejection additionally prohibited workarounds, indirect execution, raw CDP,
alternate browser surfaces or policy circumvention. No workaround was attempted.
A read-only URL/title check afterward still showed the original Phase 1 URL/title;
no successful Phase 3 copy is claimed. The retained screenshot is
`layout-copy-blocked.png` in the stage; it shows the remaining original layout,
not a Phase 3 installation. The exact action/reason is in `browser-access.json`.

**Phase 3 native compile, private save, attachment, cutoff/advance/restart parity,
later-anchor browser checks and actual runtime/drawing measurements are unexecuted.**
This is an access blocker, not a compiler failure. Phase 1's successful revision3
compile and three-date Replay record remain valid only for that original source;
they are not promoted to expanded-map verification.

Opening Pine Editor automatically restored an unrelated MNQ strategy header.
No Vern dated answer rows were shown. Layout names were visible; their contents
were not opened. No Replay date was selected in this task, and no development or
hidden-test target was opened. The original baseline/settings were not changed.

## Market-input feasibility

A separate read-only TradingView connector requested the last 5,000 ESZ2026
five-minute bars, first as summary, then retaining the response bytes. Its exposed
schema has count/interval/symbol/summary; it does not expose the historical date
paging parameters mentioned in the response hint. No unsupported parameter or
alternate endpoint was tried.

The response starts **October 6 at 14:20 New York**, after that day's cutoff and
after October 1/2/5. It also declares regular-session-only, split-adjusted prices.
Observed later days contain 276 bars, including overnight hours, so the notice
and observed scope conflict. That contradiction does not establish exact feed/
ETH/adjustment identity. The input was not accepted for primary reconstruction,
and no N1/E1 detector was run on it. Retained market bars extend through October 30;
these are neutral price inputs, not dated source targets. The diagnostic selection
is bounded by futures trading date through October 14 and has 1,688 bars.

The stage's `market-input-assessment.json` records source arguments, notice,
response/selection hashes and rejection reasons. The connector does not replace
native Pine execution. No different contract, timeframe, fabricated bars or
per-day settings were substituted.

## Local verification

The independent [specification model](../src/phase3_model.py) exercises hand-worked
N1/E1 arithmetic, invalid distributions, membership and PBT timing. It preserves
the original model and tests all 19 baseline fields under equivalent synthetic
history. [Matching tests](../tests/test_phase3_matching.py) check cardinality,
minimum interval error, deterministic ties, exact family/window strata and
compound occurrences. [Anchor encoding tests](../tests/test_phase3_anchor_inputs.py)
check manual serialization, missing/unsupported anchors and invalid inputs.
These are synthetic tests and source-byte checks, not a Pine interpreter.

Final Pine SHA-256 is
`9cf9f9a56311496ea7414758d1dd51e6e9a7af5739cffa4438c35190b1f64504`.
The stage retains 21 exact implementation/configuration/lockfile snapshots and
structured reports/logs. Its code revision plus dirty-source manifest is an
implementation retention record, not a completed research seal.

| Check | Actual result |
|---|---|
| Registered Study 29 suite | **186/186 passed**, zero skips/errors/failures; includes 43 N/E/composite/PBT model tests, 19 matching, five anchor-codec and three Pine source guards, alongside existing tests |
| Source preservation guard | Original verified Pine SHA unchanged; removing marked additions restores its source; new hooks do not directly mutate existing baseline state |
| Registry suite | **35/35 passed** |
| Documentation | **121 maintained guides**, zero errors |
| Phase 2 bounded audit | Passed: 23 entries, 21 original source paths, 143 occurrences, 2,717 descriptive comparisons, 61 Phase 1 artifacts unchanged |
| Explicit Phase 3 integrity/status audit | Four frozen files and 33 source pins match with the documented README navigation exception; 21 implementation files and ten failure records consistent. Broader 44-file check **fails** for one unrelated pivot README change, detailed below |
| Default compatibility workspace gate | Documentation passed; Bhishma failed with two existing configured-input errors; remaining four checks unexecuted after fail-fast |
| Native Pine/Replay | Not attempted after the separate-layout security rejection |

All study execution used the existing locked environment without sync:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/check-workspace --check study-29 --report work/29_verniman_level_reconstruction/phase3_20261031T003524Z/study29-checks.json
python3 -m unittest discover -s scripts/tests -p test_check_registry.py
python3 scripts/check-agent-docs.py
python3 studies/29_verniman_level_reconstruction/phase2/check_review.py
python3 studies/29_verniman_level_reconstruction/phase3/check_phase3.py
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/check-workspace --report work/29_verniman_level_reconstruction/phase3_20261031T003524Z/default-workspace-checks.json
```

The default gate discovered 983 Bhishma tests and ran 976 with two setup errors
and no skips. The missing file is
`data/raw/databento/GLBX.MDP3/symbology/continuous/volume-rank-0/2010-06-06_2026-09-20.json`;
the other error is no point-in-time ES roll-1 definition pair within its ten-day
window. Both were already recorded in Phase 1. They were not repaired or rebuilt.
Sahadeva, legacy-01, legacy-02 and vwap-doctor were unexecuted after fail-fast.
A full workspace pass is not claimed.

The broader preservation audit detected a hash change in the preexisting,
unrelated `indicator/pivot-README.md`, outside the frozen 33 Phase 1/2 pins and
outside every Phase 3 edit assignment. Its observed modification clock was
00:38:26 UTC on October 31. The task did not inspect its contents, write it or
revert it; authorship of the concurrent change is not established. Exact before/
observed hashes are in `unrelated-concurrent-change.json`. The explicit audit
retains its failure rather than silently accepting a new baseline.

Navigation metadata and generated-index inputs did not change. No metadata/index
regeneration, numerical historical rerun or Narada build was needed.

## Training, source access and preservation

All ten [training records](training-results.json) explicitly report unavailable
expanded maps. Candidate counts and cap omissions are null, not zero detections.
The first three attribute all 19 retained Phase 1 baseline fields with their saved
hashes; those are not fresh Phase 3 maps. The other seven baseline fields remain
unknown. P1/P2 have no declared supported anchors. No actual expanded source
comparison, coverage rate or first-pass detector miss is claimed.

The seven new training targets remain closed because all seven real expanded
maps have not been saved and hashed. A failure record does not unlock reveal.
Only the existing Phase 2 October 1/2/5 inventory was reviewed for metadata;
source pixels and new source tables were not reopened. It contains 143 readable
occurrences with unresolved windows, so frozen primary exact-window coverage
would be not estimable even after maps exist, until window suitability is resolved.

The protocol/settings/input declaration/decision record were frozen before new
detector execution. The frozen earlier-phase source pins match, with one explicitly recorded
exception for an additive current-phase link in the mutable study README. The
broader preexisting-file check has the separate pivot README failure above. Phase 1 original attachment, Pine/settings/model/
tests/evidence and Phase 2 cases/protocol/inventory/findings remain unchanged.
Preexisting unrelated worktree changes were left untouched by this task; the
separate detected concurrent README change is disclosed above. No research priority
assessment, publication bundle, deployment or archived run was changed.

## Official documentation and remaining limits

Reviewed current official [Pine bar states](https://www.tradingview.com/pine-script-docs/concepts/bar-states/),
[time and IANA clocks](https://www.tradingview.com/pine-script-docs/concepts/time/),
and [execution/drawing limits](https://www.tradingview.com/pine-script-docs/writing/limitations/).
Documentation supports the implementation choices; it does not establish account-
specific compilation or timing. The [Pine interface](pine-implementation.md)
records declared drawing/array bounds and extraction limits. Actual performance
remains unmeasured in TradingView. Local synthetic timing is not Pine performance.

The candidate generator is **not ready for empirical selection research** until
native execution, identified training maps and qualified source comparisons pass.
The [handoff](phase4-handoff.md) preserves those gates. No automatic LIS/pivot,
ordered targets, profitability testing, Narada publication or deployment was added.

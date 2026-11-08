# Separate source collector and final scorer instructions

These instructions are for an identified collector/scorer, separate from the
prediction operator. They do not authorize any Phase 6 source access during
preparation. No prospective source has been observed. Assign actual actors before
collection; a directory name, alternate role label or fresh chat does not itself
establish blinding or erase prior study exposure.

## Collector responsibilities during the fixed sample

Use only the exact scheduled date from [calendar.json](calendar.json), in the
logged-in in-app browser. Follow normal X UI intake: verify the established author
and stated session/contract, open the relevant dated post/revision and preserve
the visible full plan/chart, URL and clocks. Do not use X APIs, direct scraping,
hidden endpoints, other browsers, broad galleries or unrestricted tables. Do not
contact Verniman or anyone else. Do not open October's protected sources or use a
missing plan to select a replacement date.

Preserve original image/crop and text, not just extracted numbers. Record actual
collector actor, access event ID/time, post/revision/capture timestamps, visible
author/contract/session, full versus incomplete plan/crop, uncertainty and conflicts.
Keep every revision that was actually observed. Structural and closing labels,
execution arrows and recollections remain separate source classes. Preserve null
historical availability. No source price enters a prediction input or manual PBT
anchor. Never expose any scheduled source content to the prediction operator
until the complete-period gate passes.

For formal pre-open eligibility, capture the full same revision before 09:25
with contemporaneous browser/clock evidence. Retain an immutable availability
proof matching this schema, with actual values and exact file pins:

```json
{
  "schema": "abacus.study29.phase6.source-availability-evidence/v1",
  "session_date": "ACTUAL_SCHEDULED_DATE",
  "source_class": "ACTUAL_CLASS",
  "source_revision_id": "ACTUAL_REVISION_ID",
  "same_revision_authenticated": true,
  "complete_plan_capture": true,
  "timestamp_basis": "contemporaneous_browser_capture_local_clock",
  "captured_at": "ACTUAL_TIME_WITH_OFFSET",
  "available_at": "SUPPORTED_TIME_WITH_OFFSET",
  "source_artifact": {"path": "EXACT_FULL_PLAN_ARTIFACT", "sha256": "ACTUAL_SHA256"},
  "collector_actor_id": "ACTUAL_ACTOR_ID",
  "source_access_event_id": "ACTUAL_EVENT_ID"
}
```

Capture/access chronology must be consistent and at or before cutoff. This
records local evidence, not independent timestamp certification. Use the
independently-timestamped basis only with an actual certificate pin. A displayed
post/update timestamp or a later image does not authenticate an earlier revision.
The fixed tool retains certificate bytes; it does not cryptographically verify
their issuer or signature. Any independent-certification claim needs separate
documented verification, and the ordinary local-clock basis makes no such claim.
Do not fabricate `available_at` or set proof flags when a full same-revision capture
is absent. Such sources remain valuable captured-revision descriptive evidence.

Keep source artifacts/collector-only notes separate from prediction tasks and
contexts. Restrict access where the available environment permits, without
claiming that folder separation is enforcement. Log actual accesses and any
disclosure, with actual recipients, even if accidental. Keep immutable access-log
revisions; the final audit must preserve earlier actors/events exactly.
Use [the access-log template](templates/access-log.json); placeholder actors and
an incomplete audit cannot pass the reveal gate.

## Scorer responsibilities after the complete-period gate

Do not reveal/read collected contents in the prediction context before the gate.
After December 8's 16:00 New York close, account for every scheduled session,
including failures. Refresh the final actor audit within five minutes before
gate creation, after the last scheduled close; do not attest future non-access.
The gate itself reads metadata, and the scorer's later audit must preserve all
earlier events and account for subsequent accesses. Run:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/reveal_gate.py --freeze studies/29_verniman_level_reconstruction/phase6/freeze.json --ledger FINAL_LEDGER_JSON --access-log FINAL_ACCESS_LOG_JSON --output NEW_GATE_JSON
```

A failed gate stays closed. A successful post-period gate may permit descriptive
scoring of an incomplete/exposed sample while explicitly disallowing formal
prospective estimation. It does not convert missing/late/reconstructed/exposed
records into timely ones, certify operator independence or establish source fidelity.

Curate the [source-role ledger template](templates/source-role-ledger.json) using
the unchanged Phase 4 role conventions and the frozen comparison contract.
Retain every original occurrence, compound role, full target order (including
more than three targets), revision/class stratum, uncertainty and source failure.
Canonical selection uses the earliest independently captured full pre-open plan;
unresolved conflicts stay separate. Without an eligible canonical plan, preserve
all captured revisions descriptively; do not select the one nearest predictions.
Each date needs an explicit available/missing/conflicting/incomplete source status.

Pin all exact source artifacts, role ledger, gate and final audit in the
[saved-scoring input template](templates/saved-scoring-inputs.json). Keep that
manifest in the declared stage and source artifacts inside its bounded source
root. Then score saved predictions only:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study29-uv-cache ./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/score_saved.py --manifest SAVED_SCORING_INPUTS_JSON --output NEW_SCORE_DIR
```

Preserve the first pass and the complete 20-date status table. No model/selector
rerun, parameter change, post-result tolerance/denominator adjustment or source
condition repair is allowed. Report observable coordinates/roles/order separately
from strict construction/window/condition fidelity. Missing eligibility is not a
zero-percent score. Retain abstentions and all source destinations; a matched
subsequence is not complete ordered-map reproduction. No score can promote a
validated method, declare profitability or authorize publication/deployment.

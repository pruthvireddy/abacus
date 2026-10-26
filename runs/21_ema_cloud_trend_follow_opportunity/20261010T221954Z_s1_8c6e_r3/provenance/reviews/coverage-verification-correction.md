# Retained coverage-only verification correction

The original frozen r3 verification failed because `reconcile_coverage` expected
undefined three-minute feature readiness. The frozen summarizer instead merged
the separately saved decision-coverage counts into S1-T00. The original failure
is retained in `provenance/scientific-verify.log`; it is not relabeled as a pass.

For New York signal-open calendar years 2018–2020, the retained independent
adapter checks `feature_ready_slots` and `mapped_ready_slots` as the count of
saved technical rows for which both `usable` and `feature_valid` are true.
`ready_share` divides this count by all modeled scheduled slots in the year;
`ready_sessions` counts unique trading-session labels among those ready rows.
Unusable rows with valid mapped features do not count as ready. Every annual
coverage field is checked, including nominal source counts, missing, empty,
mixed-contract, calendar-invalid and known-closure counts. Annual support must
be complete and unique. For 2017 warmup, the original native five-minute
feature-valid count and undefined three-minute readiness convention remain;
mapped readiness, shares and sessions remain undefined for both intervals.

Five synthetic fixtures passed before historical verification: mapped three-minute
readiness with an unusable-but-feature-valid row, native five-minute warmup,
undefined three-minute warmup, complete annual support, and deliberate
readiness/count/share/session corruption rejection. These fixtures use no
historical outcome values.

`coverage_verification_adapter.py` imports the canonical verifier only after
checking its identity against the frozen source inventory. It replaces only
`reconcile_coverage`, calls the entire unchanged `verify_bundle`, and restores
the original function. Source guards run before and after verification. No
signal, outcome, estimator, bootstrap, selection, settings, protocol or source
inventory changes were made. Root corrected only saved presentation wording
and link/alt qualifications before final report pins were captured.

`coverage-adapter-before-execution.json` pins the adapter, fixture receipt,
original failure, settings, input/delivery/event manifests, numerical tables,
illustrated paths, final presentation files, and 27 external manifest records
before execution. Canonical source snapshots remain byte-identical. The full
run completed on 2026-10-10 at 22:49:46 UTC with all 34 checks passing:
2,289,024 technical rows, 39,178 outcomes, 2,054,632 numerical table cells,
all six primary terminal intervals at 1/4/8-week blocks, 1,332 public cells,
5,622 selected-download cells, six numerical claims and six figure bindings.

`provenance/scientific-reconciliation.json` includes the narrow adapter disclosure;
`provenance/external-bytes.json` verifies all 24 explicit retained ledgers.
`coverage-adapter-completion.json` pins both receipts. The final actual report
review is recorded in `report-review.json`; exact commands are recorded in
`reporting-review-commands.json`. These checks do not certify native chart replay,
vendor receipt timing, original raw-source reconstruction, off-device backup,
execution fills or trading profitability.

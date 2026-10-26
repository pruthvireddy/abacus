# Bhishma — Data & Features

Start with the workspace [agent map](../../AGENTS.md), the current
[architecture](../../ARCHITECTURE.md), and the [package README](README.md).

## Read and write

- Ingestion, calendars, continuous contracts, reusable causal features, loaders,
  and data validation belong in `src/abacus_bhishma/`; their tests belong in
  `tests/`. Follow the adjacent module's conventions.
- Read the relevant [dataset request](../../requests/README.md), pinned
  [catalog records](../../catalog/), and indicator specification before changing
  feature behavior. Bhishma owns dataset/feature semantics and release contracts.
- Resolve the dataset project root through the configuration described in the
  README. It is now the workspace root (`.`), with catalog records in `catalog/`
  and physical Bhishma layers directly under `data/`. The storage relocation
  preserves existing release identities and bytes; it is not a new publication.
  Follow the [data layer guide](../../data/README.md).
- A behavior or schema change requires a new release identity. Preserve existing
  releases and the workspace's byte-identical catalog snapshots.
- Study-specific event definitions, forward outcomes, execution assumptions,
  and strategy advice belong to [Sahadeva](../sahadeva/AGENTS.md) and the study.
  Route requests for reusable inputs through `requests/`.
- Continuous builders never replace final publication state, even with `force`.
  That flag recovers only their exact staging directory after conflict checks;
  manually inspect partial final output and backup/recovery artifacts. Phase 1
  publishes schedule leaves while preserving the shared Phase 2 audit parent.
  See [continuous publication maintenance](README.md#continuous-publication-maintenance).
- Shared file hashing/Git provenance belongs in `provenance.py`; the existing
  holiday rules and their required date helpers belong in `calendar.py`.
  Preserve builder compatibility imports and include executed helper sources
  in future provenance. Session bounds, regimes, and expected-minute policies
  remain with their existing consumers.
- Consumer loading belongs in `feature_loader.py`, `continuous_loader.py`, and
  the thin `vp_hvn_loader.py`. Keep canonical loader imports independent of
  builders and native activation; retain `vp_hvn_release.load_release` as a
  compatibility path. The builder import retains its runtime dependencies.
  The GC/VWAP/continuous optional manifest path and expected hash must be supplied
  together; selected-byte verification is separately opt-in. Preserve the legacy
  branch when options are absent. Loaders do not repair releases or expand the
  VP/HVN compatibility guarantees.
- Keep each publisher's explicit output/recovery inventory with its orchestration;
  `publication_safety.py` owns only shared path/refusal/new-metadata mechanics.
  Required pinned inputs are not owned outputs. Preserve failed-stage evidence
  and unrelated shared-parent siblings. Future provenance retains the declared
  helper/source and lock bytes without claiming complete dependency discovery.
  Read the [task/source/test map](README.md#focused-publication-and-consumer-maintenance).
- Declare direct runtime dependencies in the package metadata. Ruby belongs to
  the derived request reader; `clang++` belongs to explicit native activation
  and publication. Preserve hard compiler/parity failures and restore native
  state in tests. See [loader and prerequisite details](README.md#consumer-loaders-and-runtime-prerequisites).

## Verify

Study 21's reusable fixed-clock 3m/5m same-contract delivery is owned by
[ema_cloud.py](src/abacus_bhishma/ema_cloud.py) and its
[release builder](src/abacus_bhishma/ema_cloud_release.py), specified by the
[request](../../requests/inbox/same_contract_ema_cloud__1.0.0.yaml).
The new consumer loader requires a manifest identity/hash; it never repairs
published input bytes. Calendar uncertainty remains an explicit unusable quality
record and the 250-observation warmup is retained. Study labels/outcomes stay
outside Bhishma. Focused fixtures use `test_ema_cloud*.py` under this package.

The continuous 2017–2026 extension uses the separate
[1.1.0 builder](src/abacus_bhishma/ema_cloud_release_v2.py) and
[pinned public loader](src/abacus_bhishma/ema_cloud_loader_v2.py), with a new
[request](../../requests/inbox/same_contract_ema_cloud__1.1.0.yaml) and immutable
[manifest](../../catalog/datasets/same_contract_ema_cloud__1.1.0.json).
Preserve the 1.0.0 producer, loader behavior, and released bytes. The v2 loader
delegates an explicitly pinned 1.0.0 identity to its existing loader. New releases
must retain full scientific prefix parity, independent 3m/5m aggregation checks,
and source/calendar qualifications; do not reset features at processing-year or
study-period boundaries. Agreed fulfilled specifications belong in
`requests/fulfilled/`. The new focused fixtures are `test_ema_cloud_v2.py`.

Run commands from the workspace root:

```sh
./scripts/check-workspace --profile bhishma-loaders
./scripts/check-workspace --profile bhishma-safety
./scripts/check-workspace --check bhishma
```

Use focused module tests while developing; run `scripts/check-workspace` after
package, storage-path, dependency, or cross-component changes. Data creation or
downloads are separate tasks, not verification commands. For documentation-only
changes, run `python3 scripts/check-agent-docs.py`.
The README lists focused synthetic publication-safety, provenance, and calendar
tests and read-only verification limits; never test refusal by building against
the configured historical publication root.
For consumer changes, use the README's focused loader, import-boundary, and
prerequisite suites plus lock consistency and existing numerical/native checks.
Use isolated temporary packaging environments; never remove shared development
dependencies through a runtime-only sync.

The [workspace harness](../../README.md#workspace-check-harness) exposes this full
suite as `./scripts/check-workspace --check bhishma` from the root. Inspect its
declared compiler/Ruby and configured-publication scope; this is not a data-free
synthetic suite. The compatibility default remains bounded. Harness execution
uses the prepared locked environment without sync and reports actual skip reasons.
The fast profiles use exact synthetic test filenames and exclude compiler/Ruby
and configured integration suites. Study 14 import guards run with their study
owner in a separate process; package tests must not import study implementations.

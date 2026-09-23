# Session-anchored VWAP

Study `05_session_vwap` · **planned** · ES / NQ / GC

Investigate six VWAP candidate families using the pinned Session-Anchored VWAP 1.0.0 release. [The original plan](plan.md) defines events, causal timing, denominators, comparisons, uncertainty, and the proposed evaluation periods. [study.yaml](study.yaml) records the shared proposed settings; it is not an executable configuration.

Start with return-to-VWAP behavior, then compare immediate and confirmed fades, then retest bounces. The [six strategy cards](../../strategies/README.md) track the ideas separately from the study and will accumulate evidence across later runs.

## Inputs and status

[inputs.lock.json](inputs.lock.json) pins release, 2m/5m manifests, source-price manifest, and relevant contracts by SHA-256. Resolve `publication_root` through the root path configuration; physical data remains in the existing Bhishma publication. The published manifests preserve their original contents and relative partition paths. Checks of manifest identities do not substitute for data-partition validation.

No VWAP outcomes or strategy implementation have been added. No execution costs or final trading rules have been chosen. [notes.md](notes.md) records remaining decisions and changes. Before computation, freeze the protocol and evaluation assumptions, then save each execution as a distinct artifact bundle under `runs/05_session_vwap/<unique_run_id>/`.

[Artifact conventions](../../templates/README.md) · [Research library](../../reports/index.html)

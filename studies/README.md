# Research studies

A study is a defined question and protocol. A run is one execution; a strategy is an enduring idea that can collect evidence from multiple studies.

`study.json` provides the portable index metadata: unique `study_id`, `title`, `summary`, `status`, `topic`, `products`, `data_summary`, `evidence_status`, and `strategy_ids`. Optional `reference_run` is an explicit reviewed selection, never inferred from recency. Historical code remains under `legacy/sahadeva/analysis/`; the first new planned study is `05_session_vwap`.

Use the [study template](../templates/study.md). Record the protocol in `plan.md`, machine-readable settings in `study.yaml`, input identities in `inputs.lock.json`, and decisions in `notes.md`. Add executable study code only when implementation is authorized. Regenerate the [research library](../reports/index.html) with `python scripts/build-research-index.py`.

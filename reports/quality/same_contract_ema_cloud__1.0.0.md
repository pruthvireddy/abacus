# Same-contract EMA cloud input delivery 1.0.0

Input-only preparation for 2017 warmup and 2018–2020 history. No event labels or future outcomes.

Normal weekday 18–17 NY, ES/NQ 16:15–16:30 pre-2021 pause; rule-generated holiday/early-close sessions unusable, all nominal slots retained. Missing no-trade minutes are unknown gaps, never inferred closures.

Missing raw mapping and ES roll-1 definition pair prevent source reconstruction checks. No mappings invented; existing releases not rebuilt. Verified actual retained minute partitions, master, roll schedule, adjusted reconciliation partitions and adjustment schedules; selected 2017–2020 contract identity reconciles to master and rolls.

Primary 250 consecutive complete 5m observations after reset remains fixed. A 500-observation readiness and first-open seed sensitivity is saved in the immutable audit directory.

Manifest: `catalog/datasets/same_contract_ema_cloud__1.0.0.json`. Exact per-product/year coverage, exclusions, source quality, reconciliations and qualifications are saved below `data/features/ema_cloud/version=1.0.0/audit/`.

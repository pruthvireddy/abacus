# Camarilla reversals with an EMA cloud in ES NQ and GC

Study 20_camarilla_ema_cloud_reversals · Status: planned · Draft protocol 0.3.0.

The proposed historical study examines five-minute rejections at R2/S2, R3/S3
and R4/S4 in ES, NQ and GC, with a close-based EMA20/EMA50 cloud. It separates
forward price behavior from a specified trade policy, costs and stability.
The user will review the proposal before research implementation or execution.

## Review the proposal

- [Historical study plan](plan.md): dates, inputs, signal rules, EMA comparisons,
  entry/exit policy, metrics, uncertainty and implementation gates.
- [Report proposal](report-proposal.md): horizon and weekly tables, additional
  statistics, figures and the eventual Abacus publication.
- [Data inventory](data-inventory.md): verified retained coverage, candidate
  release identities and data-quality limitations.
- [Proposed machine-readable settings](study.yaml), [source input lock](inputs.lock.json)
  and [decisions](notes.md).

The main period proposed is 2018 through September 18, 2026. Development uses
2018–2020, validation 2021–2023 and final historical evaluation 2024–2025. Report
2026 recent replication and 2010–2017 historical robustness separately.
Candidate market releases are inventoried, not execution-locked. No historical
signal calculation, sealed analytical result or website publication exists yet.

## Delivered indicator

The [Camarilla Pivot Levels Pine source](pine/camarilla_pivot_levels.pine) combines
the supplied Camarilla/optional-CPR indicator with the configurable EMA cloud,
Strategy Criteria, ATR-normalized MAE/MFE horizon statistics and weekly outcomes.
It was compiled and saved privately to the user's TradingView account, with
exploratory ES five-minute acceptance recorded in
[the verification log](../../work/20_camarilla_ema_cloud_reversals/tradingview-20261008/verification.json).
It does not simulate stops, targets, fees or strategy orders.

The original pivot source is retained byte-for-byte in
[the source snapshot](reference/source_user_camarilla_optional_cpr.pine).
Screenshots are retained in ignored research storage with hashes in the input lock.
See [indicator usage and verification](pine/README.md) for the delivered behavior.
The cloud screenshot specifies five minutes and 20/50 lengths; its precise
trade-filter condition remains a proposed research choice.

The [previous protocol](reference/protocol_0.2.0.md) and
[previous settings](reference/settings_0.2.0.yaml) preserve the earlier
MES/MNQ-oriented proposal and chart-panel conventions. Protocol 0.3.0 expands
the requested historical scope to ES/NQ/GC without changing the delivered Pine.

## Ownership and verification

Study-specific research belongs here under
[Sahadeva's ownership](../../packages/sahadeva/AGENTS.md). Reusable data/calendar
work follows Bhishma's publication contract. Stage future calculations under
work/, and seal verified evidence in a unique run following
[the run guide](../../runs/README.md). Published inputs and completed runs remain
unchanged.

For this documentation-only proposal:

    python3 scripts/check-agent-docs.py
    python3 scripts/build-research-index.py --check

The earlier focused scalar Pine-helper checks use:

    python3 -m unittest discover -s studies/20_camarilla_ema_cloud_reversals/tests -v

Those tests do not emulate the full Pine series runtime and are not a historical
study engine. A later approved implementation needs the numerical, availability,
calendar, missingness and execution checks specified in the plan.

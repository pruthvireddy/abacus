# Verniman Levels — Phase 1 protocol

Study `29_verniman_level_reconstruction` · Protocol 1.0.0 · 2026-10-30

This study owns the new **Verniman Levels** candidate-map indicator. Phase 1
implements and checks a session-aware derivative of the user's supplied Pine
script. It does not establish Vern's proprietary calculations, select trades or
measure profitability. [Study 27](../27_verniman_method_knowledge/README.md)
remains the qualitative source owner.

## Scope and acceptance

Preserve the supplied baseline byte for byte, audit its actual calculations,
correct session and state handling, add explicit overnight and completed-RTH
extremes and a last-traded closing reference, and freeze a reproducible pre-open
candidate map. Keep developing references separate from saved references.
Document inputs, missing history and unsupported settings. Keep arithmetic and
terminology specifications beside the code.

Acceptance distinguishes source review, local/static checks, synthetic checks,
actual TradingView compilation and actual browser replay. Local models cannot
substitute for the last two. Complete unaffected local work if account access,
history, compilation or replay is blocked; record the exact limitation in
[verification](verification.md). Do not seal an incomplete run.

The baseline is [the retained original](reference/vp_levels_original.pine),
pinned by [its manifest](reference/source-manifest.json) and
[the input lock](inputs.lock.json). The derivative is
[Verniman Levels](indicator/verniman_levels.pine). Baseline row size of 16 ticks
and value-area coverage of 70% remain provisional engineering defaults, not
recovered or fitted Verniman settings. The more elaborate Study 14 Pine file is
an optional engineering reference and remains unchanged.

## Phase 1 calculation policy

Use chart OHLCV bars and retain the baseline's uniform allocation of each bar's
volume across touched price bins. Retain its POC and contiguous value-area
construction, including deterministic tie handling. Fix reset, readiness and
availability handling; do not relabel a POC or VA boundary as an HVE.

Use explicit New York session timestamps and identities for the fixed 18:00–17:00
futures session, 09:30–16:00 RTH and 18:00–09:30 overnight window. Limit the
initial supported configuration to standard 1-minute or 5-minute ES/MES/NQ/MNQ
futures charts with full electronic-session bars. Require complete supported
period coverage before presenting a completed period as ready. Reject or mark
missing/unsupported periods instead of carrying plausible stale values.

The pre-open cutoff defaults to 09:25 America/New_York and precedes 09:30.
Only confirmed bars whose closing timestamps are at or before the cutoff enter
the snapshot. A supported aligned cutoff has a last included bar ending exactly
at that time. The snapshot is a copy of candidates and source identities; later
developing bars cannot alter it. Drawing coordinates never backdate information
availability. See [the specification](specification.md) for the implementation
contract and intentional qualifications.

## Browser verification protocol

Use the user's logged-in TradingView in the in-app browser and a separate study
layout or a copy that preserves the user's current setup. Save the derivative
privately and attach it if account capabilities permit. Do not publicly publish.
Inspect and record actual symbol/contract, exchange/feed, session settings,
adjustment settings, standard chart type, timeframe and available history.
Consult current official Pine and Bar Replay documentation, then test actual
account capabilities rather than assuming profile/replay availability.

The only permitted baseline replay dates are **2026-10-01, 2026-10-02 and
2026-10-05**. For each:

1. Load preceding history sufficient for full current/previous weekly and
   completed daily references, including a complete preceding trading week.
2. Replay to the configured cutoff; record the frozen candidate values, last
   included bar and each family's readiness/source session.
3. Advance replay beyond the cutoff and into RTH. Verify the saved values remain
   unchanged while developing values may update.
4. Restart or reload at the same cutoff with identical settings and history;
   compare candidate values, source identities and last included bar.
5. Record missing history, unavailable families, compile/runtime errors and
   reproduction differences without substituting a more convincing date.

Stage outputs under a new `work/29_verniman_level_reconstruction/<verification-id>/`
directory. Retain exact commands, source hashes and browser evidence. This is
implementation verification, not a run comparing the candidates with Vern's
dated answers.

## Protected evaluation design

The eventual project separates two problems:

1. Generate a bounded, explainable candidate map.
2. Select a pivot/scenario divider and ordered bullish/bearish targets from it.

The proposed chronological split is training **October 1–14, 2026**,
development **October 15–20, 2026**, and hidden test **October 21–27, 2026**.
All later learning/evaluation is **planned and unexecuted** in Phase 1. Dates
remain subject to declared source-suitability checks; chart attractiveness
cannot justify substitution.

Phase 1 does not open October holdout screenshots, dated target annotations,
observation contents, extracted daily-level rows or commentary containing the
answers. It does not search the private intake or Verniman daily-level releases.
Generic conceptual knowledge-base material is allowed. Record any accidental
target exposure with its date and scope; that date loses pristine-holdout status.

## Later modules — planned, not implemented

After the baseline passes its available verification, a separately authorized
phase will use training-day examples to define HVN/LVN segmentation, candidate
HVE detection, composite balance references, PBT hypotheses and anchor selection.
A further phase will define LIS/pivot selection and ordered bullish/bearish
targets. Freeze those rules before development/hidden-test evaluation and record
source suitability, timing and revisions. No stub here produces invented HVE,
PBT, LIS or target values.

# Decision notes

## 2026-09-27 — Initial planning

- User named the study **Asia session VP levels study**, defined Asia as
  20:00–00:00 New York time, requested NQ one-minute data first, and proposed
  three setups. MAE/MFE and an elaborate plan are authorized; implementation
  and research execution await the user's next instruction.
- ES and GC are deferred. The 18:00–20:00 period builds overnight context;
  it is not the primary entry window. Volume behavior is a question to test.
- Source review established that profiles approximate volume-at-price by
  uniformly allocating bar volume and that displayed HVN selection changes
  more often than candidate rebuilding. Historical rendering is not signal
  availability evidence.
- Setup 1 clarification was requested: enter at POC and fade the return leg,
  or enter on value-area re-entry and target POC. Draft assumes the former
  provisionally; the alternative is documented separately. No protocol freeze
  or event implementation until this meaning is resolved.
- Proposed defaults: next-minute open, known pre-candle level snapshots,
  30-minute primary horizon, additional 5/15/60/120-minute paths ending by
  midnight, and separate variable-length midnight outcomes.
- Data availability inspection was read-only: catalog identities, partition
  presence, schemas, and endpoint metadata. All 17 annual NQ partitions exist
  in each selected continuous variant. No signal or outcome study was run,
  and full partition integrity has not yet been independently checked.
- Contract-native VP price coordinates, strict consumed-window completeness,
  60-minute setup expiry, 15-minute signal lockout, sample partitions, controls,
  and inference rules are proposed study choices open to revision before freeze.
- A reusable causal profile release belongs to Bhishma. No dataset request,
  feature publication, strategy recommendation, or web deployment was performed.

## 2026-09-27 — Implementation handoff and independent preparation

- The new handoff authorizes implementation, execution, new Bhishma feature
  delivery, and local reports. External publication remains outside scope.
- The required targeted setup 1 clarification was asked. The comparison family
  remains unfrozen pending that answer; no study outcomes have been inspected.
- Prepared [the feature request](../../requests/inbox/nq_causal_vp_hvn__1.0.0.yaml)
  and independently froze [feature reconstruction](protocol-features-1.0.0.md).
- Initial source hashes matched 45 consumed identities, including both sets of
  17 NQ partitions and the source indicator. Raw/adjusted identity checks are
  repeated by the builder before release; existing releases remain unchanged.
- The bounded March 2024 feature-only pilot produced 7,192 snapshots and 12,109
  candidates across both coordinate frames. Timing, mass, width, selection and
  deterministic partition checks passed. No signal cohort or outcomes were run.
- Fixed-point decoding explicitly recovers exact quarter-point prices after the
  public float conversion so roundoff cannot change a floor-based VP row.
- External TradingView feed parity, weekly boundary timestamps and equal-strength
  sort stability are not certified. The declared exchange-session adaptation and
  deterministic tie order are retained as limitations, not hidden assumptions.
- Bhishma now owns the [calculation contract](../../catalog/indicators/nq_causal_vp_hvn__1.0.0.spec.json)
  and [identical source copy](../../catalog/indicators/nq_causal_vp_hvn__1.0.0.source.pine).
  The original reference remains byte-identical. Its builder reads catalog
  contracts and source data, without depending on study configuration or code.
- Full inspection found historical 17:00–18:00 observations and dates containing
  only such observations. Weekly VP includes those chart bars; PDH/PDL and HVN
  exclude them, and no empty futures session is invented. All observations are
  retained in source publications and counted in the quality ledger.
- The percentage-boundary synthetic example uses peak heights 3 and 3/5:
  literal Pine `3*20/100` keeps the lower peak; substituting `3*0.2` can drop
  it through rounding. Both scalar and native reconstruction use the literal
  operation order. Adaptive rows wider than the zone cap are also tested.
- The historical feature export starts each evening with an unavailable HVN
  cache, then seeds at the first observed futures-minute close. The source's
  previous afternoon cache is not reconstructed for that first pre-bar snapshot.
  This declared boundary adaptation precedes the 20:00 entry window. All later
  evening caches follow the 15-minute cadence from the new-session seed.
- Full-source inspection confirmed there are no inter-date lost RTH reset
  transitions in the delivered history; per-date RTH batch reconstruction is
  therefore equivalent on this pinned input. Missing-minute histories remain
  flagged. Provider condition flags are retrospective source-quality metadata,
  not certified live features.
- Failed and superseded feature staging directories are explicitly marked as
  unsuitable for publication. Only the final audited build is delivered; none
  of these preparations has computed a real study signal cohort or outcome.

- Local feature release delivered and pinned: `nq_causal_vp_hvn__1.0.0`, manifest
  SHA-256 `3430768cda610b367ca52ca58d45c47e67ce619b773b7e54429e953f23a92eff`.
  It contains 1,383,199 evening snapshots, 2,434,496 raw/adjusted candidate
  records and 1,383,199 decision rows; there are 4,195 observed source dates.
- Nine new Bhishma numerical tests, 17 study primitive tests and the workspace
  gate passed. Full feature timing/filter/mass audit passed. The package release
  retains actual dependency/source bytes, verification logs and exact commands.
- [Preparation report](../../work/14_asia_session_vp_levels/20260927T180756Z_preparation_2281/report.html)
  and [provenance](../../work/14_asia_session_vp_levels/20260927T180756Z_preparation_2281/preparation.manifest.json)
  are staged locally. They report input quality and volume/range patterns only.
  No full study run was sealed. The signal cohort orchestration and MAE/MFE
  comparison will be completed after the required setup 1 answer and freeze.

## 2026-09-29 — Confirmed definition and local execution

- The user answered the clarification progressively: POC is the entry, buy long
  after an upper VAH excursion returns to POC, and sell short after a lower VAL
  excursion returns to POC. The opposite value-area re-entry trade targeting
  POC is outside protocol 1.0.0. The complete [protocol](protocol-1.0.0.md)
  and `study.yaml` were frozen before any real signal or outcome inspection.
- The executable uses saved pre-bar feature snapshots, actual unadjusted NQ
  next opens, strict contiguous paths, explicit late-horizon censoring and
  retrospective input-quality exclusions. All source-feature hashes were
  rechecked before outcome execution. Primary 30-minute complete events,
  controls, threshold races, and yearly funnels are retained in the local run.
- The first staging attempt stopped after saving calculations because the
  optional Markdown-table package was absent. It was marked unsuitable for
  sealing. A fresh run with built-in table formatting completed and passed
  saved-evidence verification; prespecified adjusted-coordinate and frozen-
  breakout-level cohorts were added as separately labeled sensitivities.
- The adjusted coordinate sensitivity is retrospective and not point-in-time
  certified. The 2010–2017 historical cohort is sparse under strict profile
  completeness; the quality table must accompany any interpretation. One-
  minute OHLCV cannot establish intrabar ordering, fills, or TradingView tick
  parity. No net profit or executable strategy is claimed.
- The locally sealed evidence is
  [run 20260929T124500Z_asiavp_b2](../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html).
  The primary validation evidence is inconclusive for setup A, partly supports
  B's short-side favorable excursion without a two-sided or net edge, and
  shows higher adverse excursion for C's short-side fade with uncertain
  favorable advantage. The final 2026 check is YTD and mixed. See the exact
  saved tables and intervals before using any result.

## 2026-09-29 — Previous-RTH extension

- User requested two added ideas: fade previous-day POC and continue after a
  previous-day VAH/VAL breakout/retest, with 5, 10 and 20 candle horizons,
  MAE/MFE and average close delta. The referenced image supplied the metric
  layout. The pictured approach ≥1 ATR condition was not added as a filter.
- The existing pinned release has previous **RTH** VAH/POC/VAL, not a full
  previous-futures-day volume profile. A progressive clarification was sent;
  previous RTH was used as the documented working interpretation. A second
  clarification asked whether POC contact from above means long and from below
  means short; the standard fade mapping was used as an explicit assumption.
- [Protocol 1.1.0](protocol-1.1.0.md) and [settings](study-1.1.yaml) were
  frozen before these two strategies' historical outcomes were calculated.
  The older 1.0.0 study and run remain intact. Because the prior report had
  already been inspected, all 1.1.0 years are exploratory descriptions.
- [Run 20260929T141000Z_prev_rth_de](../../runs/14_asia_session_vp_levels/20260929T141000Z_prev_rth_de/report.html)
  passed hash, event, horizon, metric and report verification. A preliminary
  staging directory was marked unsuitable before the final run. The strict
  combined-reference gate leaves no complete outcome horizons before 2018.
  In the previously inspected 2024–2025 years, the 20-bar POC-fade mean signed
  close delta was negative on both sides; the VA retest was positive for longs
  and negative for shorts, with signs shifting in 2026 YTD. These are not
  executable or cost-adjusted returns.

## 2026-10-06 — Phase 3 local publication navigation

Featured presentation: [20261006T230936Z_web14](../../reports/exports/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/20261006T230936Z_web14/publication.json) · [manifest](../../reports/exports/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/20261006T230936Z_web14/manifest.json). Stable local study route: `/studies/asia-session-vp-levels/`; immutable report route: `/reports/14-asia-session-vp-levels-20261006-web/`.

Publication-only source choice: `20260929T124500Z_asiavp_b2`. Catalog navigation is maintained in [Narada](../../apps/narada/content/studies.json). Saved findings, evidence status and research-reference metadata are unchanged. This is local static publication; no deployment or research execution.

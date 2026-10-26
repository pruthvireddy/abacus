# Decisions

- 2026-10-23: user authorized implementation and execution of this descriptive
  study. EMA6 means EMA length six, not currency future 6E. Default 5m main with
  2m comparison; timeframe preference was asked asynchronously. Include full
  Globex and the common US cash window, plus GC's 08:20–13:30 window.
- Freeze protocol and numerical source before viewing crossing outcomes.
- Existing VWAP eligibility is strict, retrospective and uneven by product;
  retain exclusions and a matched-date cohort. Never broaden/rebuild the release.
- Existing workspace has substantial unrelated dirty changes. Preserve them;
  retain the scientific source actually used and Git revision/status/diff.
- 2026-10-23: the first two attempts failed before crossing outcomes were
  produced or examined. Retained stage `20261023T201700Z_ema6_v1` failed during
  input preparation with `KeyError: assets`: suffix matching mistook the daily
  indicator definition for its dataset manifest. Exact dataset-path selection
  corrected this. Stage `20261023T202000Z_ema6_v1` failed because pandas treated
  `5m` as five month ends rather than minutes. Explicit `5min`/`2min` aggregation
  aliases and a synthetic minute-aggregation test corrected this. Both incomplete
  stages remain under `work/`; all reported crossing results came from the third
  stage, `20261023T202400Z_ema6_v1`.
- 2026-10-23: the [independent version 2 review](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/saved-evidence-verification.json)
  passed reconstruction of 2,935,674 saved bars, 63,404 crossings and 43,652 panel
  rows, together with segmented summary/calendar/distribution tables, input
  eligibility, ATR availability/ranks/bins and 18 bounded source-EMA session
  samples. Version 2 corrects minute aliases in the independent source-EMA
  sampler. The originally frozen verifier remains retained; the reviewer update
  changed no final execution calculations, settings or saved numerical results.
- 2026-10-23: all [16 owned synthetic tests](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/numerical-tests.log)
  passed, including the separately selected owned harness suite. The workspace
  default gate retained two pre-existing Bhishma integration failures: a missing
  historical roll-map and a missing point-in-time contract-definition pair.
  The [check records](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/checks.json)
  preserve that failed gate and the passed explicit remaining checks; a study
  pass does not imply the full workspace gate passed.
- 2026-10-23: selected sealed run `20261023T202400Z_ema6_v1` as this study's
  explicit reference after its numerical suite, independent reconstruction and
  pinned-input checks passed. The sealer's `abacus.evidence/v1` integrity check
  verified 100 inventoried artifacts; byte integrity is distinct from scientific
  checks. The [report](../../runs/28_globex_ema_crossings/20261023T202400Z_ema6_v1/report.md)
  retains modest/inconsistent prior-ATR separation, the stronger retrospective
  quiet-versus-active difference, unequal product coverage and small monthly
  cells. This is descriptive evidence without trade returns or a strategy-card
  recommendation. Completed run bytes remain unchanged.

- 2026-10-23: user corrected the intended chart timeframe to three-minute closes,
  with EMA length six unchanged. Protocol 1.1.0 freezes this correction before
  any 3m outcomes. Keep original 5m/2m evidence unchanged. Derive interval-matched
  3m HLC3/volume Globex VWAP from the pinned minute source with existing Bhishma
  numerical helpers in memory; preserve the exact prior eligibility and ATR
  classification. No publisher or reusable-release change is needed. GC-day
  bar-open membership is 08:21–13:27, with complete bars ending at 13:30.

- 2026-10-23: before the main execution freeze, independent-verifier smoke
  checked one actual pinned ES source session (2021-06-28) for 3m OHLCV/VWAP
  parity. Direction plumbing used an in-session-seeded EMA rather than the
  protocol's continuous warmed EMA. No valid-protocol crossing count, regime
  relationship or research summary was examined and no parameter was tuned.
  The main execution retains the complete final producer and reviewer bytes.

- 2026-10-23: selected corrected 3m run `20261023T210215Z_ema6_3m_v1` as the reviewed
  reference after 25 synthetic tests and independent v3 checks passed. V3
  reconstructed all 1,397,940 bars from minute OHLCV, every anchored VWAP and
  strict direction, all 32,006 crossings and 21,826 panel rows, summary/year/month/
  distribution/bootstrap cells, nine warmed source-EMA sessions, and unchanged
  eligibility/ranges/ATR values and labels against the original run. The reviewer
  process exit was captured as zero. Fresh default workspace checks retained two
  existing historical data-integration failures; five explicit remaining checks
  passed. Both figures were visually inspected. New 107-artifact and original
  100-artifact integrity assessments passed; completed original bytes unchanged.
  This replaces the timeframe interpretation for current advice and navigation,
  without overwriting the earlier 5m/2m evidence. No trade returns or deployment.

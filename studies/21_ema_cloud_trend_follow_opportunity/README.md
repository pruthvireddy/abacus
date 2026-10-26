# 20/50 5minEMA Cloud Trend Follow Opportunity Study

Study 21_ema_cloud_trend_follow_opportunity · Stages 1 and 2 completed · Plan version 0.1.0 · October 10, 2026.

Study trend continuation after touches of a five-minute EMA20/50 cloud in ES,
GC and NQ, using three-minute and five-minute signal candles. Each stage should
produce interpretable MAE/MFE evidence and a compact report source that Narada
can render after a separate publication instruction.

Read the [full staged plan](plan.md) and [planning decisions](notes.md). The
[supplied Pine source](reference/ema_cloud_trend_follower_user.pine) is a preserved
reference; it is not an implemented Abacus research engine.

| Stage | Question | Fixed scope |
| --- | --- | --- |
| 1 | What follows a slow EMA pullback touch? | ES minimum width 2.4 points; NQ 10; GC 2.0; 3m/5m signal candles |
| 2 | How do fast and slow touch opportunities differ? | Same data, gateways, horizons and signal conventions; separate touch streams |
| 3 | Which cloud-width gateways and horizons give more reliable outcomes? | Bounded absolute/ATR width grid, chronological selection and reserved evaluation |

The cloud timeframe is five minutes in all six product/candle combinations.
MAE/MFE measure subsequent price paths from the signal close; they do not imply
executed trades, stops, targets or net profitability.

## Completed Stage 1 evidence

Sealed run [20261010T221954Z_s1_8c6e_r3](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/manifest.json):
[offline report](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/report.html),
[Markdown report](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/report.md),
[H15 and horizon scorecard](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/tables/S1-T02_horizon_scorecard.csv),
[uncertainty](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/tables/S1-bootstrap.csv),
[comparison estimates](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/tables/S1-comparisons.csv),
and [private Narada source](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/publication.json).
All required tables and six figures are retained beside the report.

The 5,257 accepted slow-touch events produced 5,238 completed primary H15 paths
and 19 censored paths. All six pooled four-week 95% intervals for mean signed
terminal movement include zero; mean MAE exceeds mean MFE in every pooled cell.
Equal-active terminal contrasts are inconclusive. Side/session negatives and
block sensitivities are retained; pooled ambiguity does not describe every
subgroup. Mapped decision readiness improves sharply toward 2020, and GC's early annual support
is sparse. This evidence does not establish stable positive continuation or
executable profitability. H15 is 45 active minutes on 3m and 75 on 5m.

The [frozen run protocol](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/protocol.md)
and [input lock](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/inputs.lock.json)
are authoritative for this run. The immutable delivery is
`same_contract_ema_cloud` version `1.0.0`, manifest SHA-256
`59010a558b4e727dbfaa37a64b4a209590288f23744127ab98747cd27ff56d44`.
Its published-input and original producer snapshots remain distinct from later
canonical source corrections.

The executed source passed 58 study fixtures and 12 feature fixtures with no
skips. Independent reviews checked all 39,178 outcome rows, required summary
and exact quantile/stability cells, publication cells/claims/downloads/figures,
and explicitly retained external ledger bytes. Separate receipts declare the
precise uncertainty verification scope: all 4,212 bootstrap intervals and 486
comparison rows passed an independent reference, and all 181,620 coverage
support cells passed an independent overlay review. Narada verify/test/lint/build and a
read-only publisher dry-run passed; browser review checked the offline report.
The compatibility gate remains failed on two existing raw reconstruction
prerequisites; its four later checks passed separately. Tooling's 189 fixtures
passed. Original vendor/mapping-arrival timing, annual holiday certification,
native TradingView equivalence and off-device backup remain unverified. See
[recorded checks](../../runs/21_ema_cloud_trend_follow_opportunity/20261010T221954Z_s1_8c6e_r3/provenance/checks.json).

A coverage-only verifier correction was separately pinned before review and
executed against the unchanged frozen ledgers, tables and estimators. The
original failed checker and both preceding diagnostic attempts remain retained.
Current checker/caption repairs are for subsequent runs; they do not alter this
completed source snapshot. Never rerun a completed bundle into its saved paths.

## Completed Stage 2 evidence

Sealed comparative run [20261011T002602Z_s2_c1b4](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/manifest.json):
[offline report](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/report.html),
[Markdown report](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/report.md),
[standalone scorecards](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/tables/S2-T02_horizon_scorecard.csv),
[branch contrasts](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/tables/S2-T08_branch_contrasts.csv),
[geometry/membership](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/tables/S2-T07_geometry_membership.csv),
[episodes](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/tables/S2-T09_episode_pairing.csv),
[union/overlap](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/tables/S2-T10_union_overlap.csv),
and [private Narada source](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/publication.json).
The report includes six saved-evidence figures and links to all required tables;
private claim/cell/figure bindings and four bounded downloads are retained.

Fast EMA20 produced 17,430 accepted opportunities, 17,332 completed H15 paths and
98 censored paths; slow EMA50 retained 5,257, 5,238 and 19 respectively. All six
primary pooled-direction, event-weighted H15 fast-minus-slow signed-terminal
contrasts include zero in both four-week pointwise 95% and Bonferroni familywise
intervals (99.1666667% marginal coverage). All adjusted one/eight-week sensitivities
also include zero; two pointwise sensitivities exclude zero. Session balancing
reverses three primary point estimates. Mean MAE exceeds mean MFE in all twelve
pooled branch cells. More observations do not establish stable positive
continuation or executable profitability; raw-point effects stay product-specific.

The timestamp/direction union has 21,901 observations, including 786 dual accepted
bars and 16,644 incremental observations beyond slow. Dual outcomes agree exactly
at every fixed horizon. Geometry, accepted membership and retrospective episode
labels remain distinct. The 5,206 completed H15 first-pair observations have
negative fast-minus-slow terminal means in every cell, conditioned on both scoped
first events and completed paths at different clocks; these are a different
population from the primary branch contrasts. Missing/reset/endpoint episodes
retain unresolved labels, and later geometric contact differs from later accepted
slow signals. Coverage shifts and sparse early GC support persist.

[Exact slow parity](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/provenance/slow-baseline-parity.json)
checked all 24 inherited ledgers and nine tables: 235,472,648 scientific cells,
zero mismatches and zero tolerance, excluding only declared wrapper fields.
All six mapped rosters (2,289,024 rows) reproduce the Stage 1 support exactly.
The registered 128 study fixtures and 12 feature fixtures passed without skips.
[Full scientific verification](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/provenance/scientific-reconciliation.json)
independently replayed events, all 169,142 forward-outcome rows, membership,
episodes and union, and reconciled summaries, coverage, uncertainty and selected
source transfers. A separately pinned adapter defers successful diagnostic
message formatting; four equivalence and 19 unchanged checker fixtures passed.
The original partial verifier attempt and its disposition are retained. Research
source and numerical outputs were unchanged. Independent numerical comparisons
retain the declared 2e-10 relative/absolute tolerance; inherited parity and dual
path equality use exact comparisons.

Private publication contract/dry-run, Narada verify/test/lint/build, actual display
review, declared local bundle bytes and all 72 retained external ledger bytes
passed their separate checks. The compatibility gate's two existing reconstruction
prerequisites remain unavailable; its four later checks passed separately, as did
189 tooling fixtures. Original reconstruction/arrival evidence, annual-calendar
certification, native TradingView equivalence and off-device backup remain
unverified. [Recorded checks](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/provenance/checks.json)
declare each scope and preserve failed preparatory attempts.

This run is the explicit current reference because it adds the comparative fast,
geometry, union and episode evidence while pinning exact slow parity to the
Stage 1 baseline linked above. Its selection follows that evidence purpose.

## Current scope

Stage 2 executed independent fast/slow comparisons under the frozen protocol
0.1.0-stage2.0 and reused immutable `same_contract_ema_cloud` version `1.0.0`.
The [Stage 2 entry point](run_stage2.py) gates fast outcomes on full exact slow
parity, preserving Stage 1 artifacts, event IDs and inherited estimands. Geometry,
membership, union and shared-episode metadata never alter stream state. The
[Stage 3 handoff](../../runs/21_ema_cloud_trend_follow_opportunity/20261011T002602Z_s2_c1b4/stage3-handoff.json)
pins both development baselines and reusable inputs, and leaves 2021–2023
validation, 2024–2025 final evaluation and 2026 through September 18 recent
replication outcomes reserved. Stage 3 grid/fold/objective execution, earlier
outcome extensions and public staging/deployment require their own scope.

The user separately authorized Stage 1 implementation, reusable inputs, numerical
testing, 2018–2020 execution, private report preparation and verified sealing.
The [executed protocol](protocol-stage1.md) and [frozen settings](config-stage1.json)
apply the [plan](plan.md), including a conservative calendar qualification before
outcomes. Stage 2 is completed; Stage 3 and public staging/deployment remain separately scoped.

The proposed main history is 2018 through September 18, 2026. Stage 1 and Stage 2
reports use 2018–2020 development outcomes; later periods remain reserved for
this study's Stage 3 selection/evaluation. Earlier 2010–2017 history is a separate
quality-qualified robustness extension. Prior Abacus research has already used
parts of the later market history, so it cannot be called pristine holdout data.

## Ownership and verification

Follow the [study guide](../AGENTS.md), [Sahadeva guide](../../packages/sahadeva/AGENTS.md),
[Bhishma guide](../../packages/bhishma/AGENTS.md), [data layers](../../data/README.md)
and [architecture](../../ARCHITECTURE.md). Reusable bars/features belong to
Bhishma; event rules and forward outcomes belong to this study; Narada consumes
only explicitly selected saved report content.

The Stage 1 [entry point](run.py) and Stage 2 [entry point](run_stage2.py) separate
freezing, scoring, saved-evidence summarizing,
rendering, scientific verification and sealing. Numerical ownership is in
[src](src/); fixtures are in [tests](tests/). Run the registered suite in its own
locked process without synchronization:

```sh
UV_CACHE_DIR=/private/tmp/abacus-study21-uv-cache ./scripts/check-workspace --check study-21
```

Reusable preparation is owned by Bhishma's
[EMA cloud module](../../packages/bhishma/src/abacus_bhishma/ema_cloud.py), with a
[new request](../../requests/inbox/same_contract_ema_cloud__1.0.0.yaml). Its loader
requires an explicit manifest pin and verifies selected bytes. Scientific
reconciliation and explicit external-ledger byte checks remain separate from
the workspace numerical-test recorder, which does not support study 21.
Figure rendering uses separately inventoried existing cached plotting packages;
numerical calculation uses the unchanged prepared locked environment.

Completed evidence follows the [run lifecycle](../../runs/README.md) and
[artifact conventions](../../templates/README.md). Publication follows
[Narada's contract](../../docs/narada.md). Preserve all prior studies, datasets,
runs, exports and unrelated workspace changes.

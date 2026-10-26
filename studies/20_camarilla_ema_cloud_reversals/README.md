# Camarilla reversals with an EMA cloud in ES NQ and GC

Study 20_camarilla_ema_cloud_reversals · Status: completed · Executed protocol
0.3.0-executed.2 · Run `20261008T220932Z_cb2711`.

The user's 2026-10-08 execution instruction supersedes the earlier planning-only
scope. This study implements and executes five-minute Camarilla rejection paths,
four EMA20/50 comparisons and a separate one-position assumed-cost policy in
ES, NQ and GC. Hosted deployment requires a separate publication instruction.

## Actual evidence

The six primary final-evaluation contrasts support no positive alignment gain.
R3/S3 alignment has 49 ES, 55 NQ and 40 GC completed 15-bar paths; every cohort is
sparse. NQ's adverse alignment-minus-none path contrast survives four/eight-week
familywise intervals, while its one-week interval includes zero. All reference-cost
alignment policy 95% intervals include zero. Excursions do not establish achievable
profitability. Retained mapping arrival times and individually certified annual
holiday calendars are unavailable; results remain historical descriptive evidence
and assumed-fill simulations.

- [Full Markdown report](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/report.md)
  and [offline HTML report](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/report.html).
- [Dated interpretation](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/advice.md),
  [table index](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/metrics.json),
  [coverage](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/tables/coverage_summary.csv),
  and [six contrasts and block sensitivities](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/tables/primary_contrasts.csv).
- [Frozen protocol](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/protocol.md),
  [settings](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/config.json),
  [input lock](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/inputs.lock.json),
  [artifact checksums](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/manifest.json),
  and [private ledger locators](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/events.manifest.json).
- [Selected contract-1.1 source](../../runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/publication.json)
  supplies the local Narada `/studies/camarilla-ema-reversals/` page and immutable
  `/reports/camarilla-ema-20261008t220932z-cb2711/` route. Raw vendor bars and private
  event ledgers are excluded from that bundle.

Development 2018–2020, validation 2021–2023, final evaluation 2024–2025, recent
replication through September 18, 2026 and earlier robustness from June 7, 2010
remain distinct. All 111 consumed records were hash-verified; five-minute
aggregation and lineage cross-checks matched for each product. T00–T14 preserve
coverage, all core horizons/sides/levels/cloud modes, annual/weekly/monthly rows,
threshold ordering, policy/cost/latency scenarios and bounded controls. There are
144 policy configurations per product. No final-evaluation retuning occurred.

## Reproduce and verify

From the workspace root, using the locked Python environment and configured
Bhishma storage paths:

```sh
bash runs/20_camarilla_ema_cloud_reversals/20261008T220932Z_cb2711/reproduce.sh
.venv/bin/python -m unittest discover -s studies/20_camarilla_ema_cloud_reversals/tests -v
```

The reproduction script freezes a fresh unique work directory, audits inputs,
scores, summarizes, selects examples, renders figures/reports and verifies them.
It does not overwrite a run or deploy a website. The code snapshots, environment
lock, actual commands, tests and source-cell reconciliation are retained in the run.

Read [executed resolutions](executed-protocol.md), [unchanged draft 0.3.0](plan.md),
[original settings](reference/settings_0.3.0.yaml), [report specification](report-proposal.md),
[input inventory](data-inventory.md) and [decisions](notes.md). The unsealed first
attempt is retained as invalidated diagnostic work; it contributes no findings.

Narada verification uses Node 24 and its independent npm lockfile. From
`apps/narada`, run `npm run verify`, `npm test`, `npm run lint`, `npm run build`
and `PORT=4174 npm run preview`. Numerical research code never runs in the app.

## Preserved indicator and ownership

The [Camarilla Pivot Levels Pine source](pine/camarilla_pivot_levels.pine),
[original source snapshot](reference/source_user_camarilla_optional_cpr.pine) and
private TradingView acceptance record at
`work/20_camarilla_ema_cloud_reversals/tradingview-20261008/verification.json`
remain unchanged. The acceptance record is ignored by Git and requires the
separately retained local workspace files. Chart-local statistics are exploratory observations, separate
from this historical engine; they do not simulate stops, targets or costs.
See [indicator usage](pine/README.md). Protocol/settings 0.2.0 remain under reference/.

Study-specific code/tests stay here under [Sahadeva](../../packages/sahadeva/AGENTS.md).
Inputs use [Bhishma](../../packages/bhishma/AGENTS.md) public loaders. New work stages
under work/; completed evidence follows the [run guide](../../runs/README.md), with
large private ledgers retained in configured data/research/sahadeva/ storage.
Preserve published datasets, existing runs and unrelated workspace changes.

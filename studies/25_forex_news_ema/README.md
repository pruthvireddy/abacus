# Forex News: EMA direction around U.S. and local releases

The completed descriptive extension provides a saved report for each of 6E,
6B, 6J, 6A, 6C and 6S using the improved saved per-future observations from
`tv-indicators/forex_news/per_future_news`. New descriptive aggregation covers
event type, ISO week, month, side, weekday, release hour, quarter and year, with
combined, U.S.-only and local-only modes kept separate. Read the
[per-future protocol](protocol-per-future-v2.md),
[frozen configuration](config-per-future-v2.json) and
[input pins](inputs-per-future-v2.lock.json) before execution.

Run `20261017T193830Z_perfuture25_d2c74b` is sealed; its
[report](../../runs/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/report.md) and
[summary](../../runs/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/summary.json)
retain 702 combined contract/timestamp observations, 1,410 overlapping mode/event
selections and 7,050 event/horizon rows. Its six immutable sealed publication-source
IDs are `forex-news-6e-20261017-v2`, `forex-news-6b-20261017-v2`,
`forex-news-6j-20261017-v2`, `forex-news-6a-20261017-v2`,
`forex-news-6c-20261017-v2` and `forex-news-6s-20261017-v2`.
The [independent numerical check](../../runs/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/scientific-verification.json)
reconstructed 22,405 aggregate rows across 72 tables and reconciled 1,930 original
summary rows; 20 synthetic numerical tests passed. The
[independent publication audit](../../runs/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/independent-publication-audit.json)
checks selected cells and retained source pins. The evidence bundle contains 943
declared artifacts. These checks establish descriptive aggregation and transfer
integrity; they do not rerun prices, signals, historical calendars or TradingView
exports. Hosted publication follows the separate Narada release gates.

The selected web bundles use presentation-only `-v2-r1` publication IDs, from
attribution revisions under `reports/exports/25_forex_news_ema/` for the same
sealed run. Each changes only the publication ID and canonical `sahadeva`
producer attribution; report values, cell mappings, charts and CSV bytes retain
the sealed evidence. The completed run and its `-v2` sources remain unchanged.

| Contract | Selected publication | Saved presentation revision |
|---|---|---|
| 6E | `forex-news-6e-20261017-v2-r1` | [6E attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6e_r1/manifest.json) |
| 6B | `forex-news-6b-20261017-v2-r1` | [6B attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6b_r1/manifest.json) |
| 6J | `forex-news-6j-20261017-v2-r1` | [6J attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6j_r1/manifest.json) |
| 6A | `forex-news-6a-20261017-v2-r1` | [6A attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6a_r1/manifest.json) |
| 6C | `forex-news-6c-20261017-v2-r1` | [6C attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6c_r1/manifest.json) |
| 6S | `forex-news-6s-20261017-v2-r1` | [6S attribution revision](../../reports/exports/25_forex_news_ema/20261017T193830Z_perfuture25_d2c74b/20261017T205500Z_attribution_6s_r1/manifest.json) |

## Preserved original import

This study imports the final saved cross-currency News EMA Move analysis from
`tv-indicators/forex_news`. It preserves the source evidence and indicator code,
then presents selected saved results through Narada. The source review is complete;
the empirical calculations were imported and have not been rerun or independently
revalidated in Abacus. See the [plan](plan.md) and [decision notes](notes.md).

The reviewed run is
`20261017T190030Z_import25_4b8a21`; its [offline report](../../runs/25_forex_news_ema/20261017T190030Z_import25_4b8a21/report.html)
and [original final report](../../runs/25_forex_news_ema/20261017T190030Z_import25_4b8a21/source-report.txt)
keep authored presentation and the unchanged original wording separately identifiable.
Its preserved earlier publication is `forex-news-ema-20261017-v1`.

The sample has 64 shared U.S. release timestamps from October 24, 2025 through
October 14, 2026, six currency futures and five horizons. The completed 15-minute
bar ending at a release supplies EMA20/50 direction and the benchmark entry close.
The candle opening at the release is the first measured candle. H5/H10/H15/H50/H100
count actual following chart candles, including exchange breaks and weekends in
elapsed time. MFE/MAE describes excursions and is not profit factor. Ticks across
instruments have different specifications and are not dollar returns.

## Per-future ownership and verification

[per_future.py](per_future.py) owns staged execution and evidence lifecycle;
[src/per_future_stats.py](src/per_future_stats.py) owns study-specific aggregation;
[per_future_verify.py](per_future_verify.py) independently reconstructs the saved
statistics without calling the production aggregate function.
[per_future_report.py](per_future_report.py) projects verified saved tables into
six reports and checks every displayed or selected cell;
[per_future_figures.py](per_future_figures.py) draws saved chart inputs.
[per_future_publication_verify.py](per_future_publication_verify.py) independently
checks the six selected reports, their cell bindings and retained original-source
pins.
[revise_attribution.py](revise_attribution.py) prepares the later presentation
revisions; [per_future_revision_verify.py](per_future_revision_verify.py) checks
their exact permitted metadata changes and unchanged selected assets.
These responsibilities stay outside Narada. The
[synthetic numerical tests](tests/test_per_future_stats.py) check denominators,
period ownership, quantiles, empty groups and Mixed-category attribution.

```sh
./scripts/check-workspace --context study-25
./scripts/check-workspace --check study-25
```

The registered suite uses the existing locked Python environment without sync
and synthetic fixtures only. A passing suite does not authorize another market
study or establish the accuracy of retained full-year prices. Real-ledger
verification, the source-cell audit, evidence integrity and web publication checks
remain separate. Follow the [run lifecycle](../../runs/README.md) and
[Narada workflow](../../docs/narada.md) before sealing or publishing.

## Original import ownership and commands

[import_report.py](import_report.py) uses the standard library to copy and hash
explicit saved evidence, project cells, author the report, verify transfers and
seal a new run. [render_figures.py](render_figures.py) uses Matplotlib only to draw
already saved values into PNGs; it does not calculate research statistics.
The source scripts are retained as evidence, never executed by this importer.

```sh
PYTHONPATH=/private/tmp/abacus-forex-plot-20261017 python3 studies/25_forex_news_ema/import_report.py prepare --run-id 20261017T190030Z_import25_4b8a21 --source /Users/ppanati/Documents/projects/tv-indicators/forex_news --figure-python /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
python3 studies/25_forex_news_ema/import_report.py finalize --run-id 20261017T190030Z_import25_4b8a21 --node /Users/ppanati/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
python3 studies/25_forex_news_ema/import_report.py seal --run-id 20261017T190030Z_import25_4b8a21
python3 studies/25_forex_news_ema/import_report.py check --run-id 20261017T190030Z_import25_4b8a21
```

The first three commands refuse replacement of prepared or sealed evidence. For
another import, use a fresh run and publication ID. `check` is read-only. It checks
the declared artifact inventory, every mapped publication/CSV/figure input cell,
and source/output pins; it does not rerun EMA reconstruction, outcome calculations,
native TradingView checks or historical validation. Selected public assets contain
summaries only; event ledgers, historical inputs and private source locators remain
in the research evidence. Publication/deployment follow Narada's separate workflow.

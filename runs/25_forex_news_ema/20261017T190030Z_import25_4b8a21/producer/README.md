# Forex News: EMA direction around U.S. releases

This study imports the final saved cross-currency News EMA Move analysis from
`tv-indicators/forex_news`. It preserves the source evidence and indicator code,
then presents selected saved results through Narada. The source review is complete;
the empirical calculations were imported and have not been rerun or independently
revalidated in Abacus. See the [plan](plan.md) and [decision notes](notes.md).

The reviewed run is
`20261017T190030Z_import25_4b8a21`; its [offline report](../../runs/25_forex_news_ema/20261017T190030Z_import25_4b8a21/report.html)
and [original final report](../../runs/25_forex_news_ema/20261017T190030Z_import25_4b8a21/source-report.txt)
keep authored presentation and the unchanged original wording separately identifiable.
The selected publication is `forex-news-ema-20261017-v1`.

The sample has 64 shared U.S. release timestamps from October 24, 2025 through
October 14, 2026, six currency futures and five horizons. The completed 15-minute
bar ending at a release supplies EMA20/50 direction and the benchmark entry close.
The candle opening at the release is the first measured candle. H5/H10/H15/H50/H100
count actual following chart candles, including exchange breaks and weekends in
elapsed time. MFE/MAE describes excursions and is not profit factor. Ticks across
instruments have different specifications and are not dollar returns.

## Ownership and commands

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

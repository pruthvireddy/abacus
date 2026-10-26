News EMA Move: cross-currency futures comparison

Rebuild all available native_6*.csv files in this folder, adding the previously
verified 6E baseline automatically:

    python3 forex_news/cross_currency_news_study/analyze.py

For an explicit subset or another destination:

    python3 forex_news/cross_currency_news_study/analyze.py \
      --input 6E=forex_news/news_ema_move_checks/native_news_ema_move_archive.csv \
      --input 6B=forex_news/cross_currency_news_study/native_6B.csv \
      --output /private/tmp/news_ema_comparison

CSV inputs must export News EMA Move on standard CME continuous futures
15-minute candles with Signals to measure = All, the default six U.S. news
groups enabled, ECB groups disabled, and the default 365-day lookback. The script
audits every selected event timestamp and component count against the embedded
calendar archive. It checks both EMA recurrences and confirms each direction
uses the EMA20/50 values of the candle closing at the news time.

Entry is that candle's close. Only the next H actual chart bars enter the MAE,
MFE, and signed final-close calculation. H = 5, 10, 15, 50, or 100. The event
candle is included and the entry candle's earlier high/low are excluded. Every
timestamp is a separate observation; overlapping windows do not truncate each
other. Simultaneous release components are one observation. A short in 6J is
a short in USD-per-JPY yen futures, with no spot USDJPY signal inversion.

Use overall.csv rows with scope = common_events for cross-instrument comparisons.
For each horizon, these require the identical UTC event timestamps and complete
post-entry windows in every supplied instrument. scope = all_available reports
each instrument's available history separately. A partial window contributes to
signals, never to the completed averages or percentages. summary.json records
each input's SHA256, first/last bar, direction counts, missing coverage reasons,
and common event cohort. Different tick values do not imply equal dollar risk.

Distance columns include raw price units, standard outright futures ticks, and
percentage of each individual event's entry price. The ratio is average raw MFE
divided by average raw MAE, not an average of per-event ratios. Percentage
distances are individually normalized before averaging. Pips are included for
6E to reconcile the earlier 6E study; no spot-JPY pip convention is imposed on
6J. --tick SYMBOL=SIZE and --pip SYMBOL=SIZE can override display normalization.
Default ticks are 6E .00005, 6B .0001, 6J .0000005, and 6S/6C/6A .00005, as
checked against official CME product specifications by the product review.
Source: https://www.cmegroup.com/markets/fx/fx-product-guide (Futures Majors).
No contract quantities or dollar returns are assumed.

Outputs:
  events.csv       One frozen entry per symbol/news timestamp.
  horizons.csv     Every entry/horizon, including completeness and all units.
  overall.csv      Every symbol/horizon in available and common-event scopes.
  by_category.csv  The same statistics by scheduled news group.
  monthly.csv      The same statistics by entry month in America/Chicago.
  summary.json     Provenance, checks, cohort, metrics, and limitations.

This compares the same six U.S. news groups across currencies. It does not yet
test domestic central bank, inflation, or employment news for each non-U.S.
currency. Historical dates are corrected calendar records rather than an
as-announced schedule vintage. Continuous futures are back-adjusted; pre-news
closes are analytical entry benchmarks. No fills, stops, targets, costs, or
profitability claims are modeled. MFE/MAE ratios are excursion descriptions.

For the full year, first save older native exports as native_SYMBOL_older.csv
beside the primary files, then run:

    python3 forex_news/cross_currency_news_study/extend_history.py

This uses the native older EMA20/50 seed and continues that state through all
merged OHLC. Prices are aligned to the current export using an audited constant
offset on overlapping bars. Discontinuous or non-overlapping sources fail.
It confirms every native selected direction still agrees, records the numeric
EMA difference caused by the current export's initial warmup, and regenerates
the default calendar entries over the final primary file's 365-day window.
No unavailable OHLC or invented warm-start EMA values are used.

Full-year outputs are under extended_year/, including reconstructed_SYMBOL.csv
and reconstruction_audit.json with source hashes, overlap residuals, seed source,
and native-direction reconciliation. These reconstructed CSVs are analytical
inputs, not direct TradingView indicator exports. The native57/ folder preserves
the shorter, directly exported 57-event comparison for audit.

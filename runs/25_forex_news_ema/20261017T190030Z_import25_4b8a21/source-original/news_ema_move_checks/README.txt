NEWS EMA MOVE — USAGE AND VERIFICATION

Indicator source: ../news_ema_move.pine
Use a standard 15-minute chart. The EMA cloud uses the same chart's EMA20
and EMA50 by default; both lengths can be changed in Inputs.

Entry rule
At the close immediately before a selected release, use the confirmed cloud
direction: fast EMA above slow EMA = Buy; below = Sell; equal = skip.
An 08:30 release uses the 08:15–08:30 candle close as the modeled entry.
The 08:30 candle is the first measured candle. Earlier movement inside the
entry candle is excluded. No touch, rejection, cooldown or thickness filter
is applied. The selected side stays fixed through every measurement horizon.

Simultaneous selected releases share one observation. Separate release times
are independent observations, so they can overlap. A later event or opposite
cloud does not end an earlier observation. Off-grid releases are skipped
rather than measured using a partly pre-release 15-minute candle.

Tables
Bottom right: horizons 5, 10, 15, 50 and 100 chart bars by default; completed
N, average MFE, average MAE, signed close change, favorable-close percentage,
MFE greater than MAE percentage, and average-MFE / average-MAE ratio.
Bottom left: eight monthly periods, using a five-bar horizon by default.
Switch to Weekly, change the period horizon or select Buy/Sell in Inputs.
The highlighted overall row corresponds to the period table's horizon.
Only completed horizons enter averages and percentages. Signals includes
entries still awaiting completion. Month/week ownership follows entry close.
Auto units displays pips on 6E/M6E; one pip is 0.0001. Ticks and Points are
also available. Five 15-minute bars means 75 minutes when trading is
continuous. Horizons count actual chart bars across session breaks/weekends.

Default selected news
U.S. employment report (payrolls, unemployment and earnings), CPI/core CPI,
FOMC decision/statement/projections, post-FOMC press conference, U.S. flash
PMI and ISM manufacturing. ECB decisions and conferences are optional.
Minutes, accounts, speeches, ADP and annual payroll revisions are excluded.

Calendar sources
Historical releases inside October 17, 2024–October 16, 2026 UTC use the
audited TradingView calendar from the prior study. That compact archive is
embedded in the Pine source; no external upload or API key is needed.
The original Forex Factory/Pine Seeds feed supplies dates after the archive
ends. It cannot override historical archive entries or add stale duplicates.
The archive preserves corrected release dates, rather than an as-announced
calendar vintage. It has no price or outcome-based event selection.
news_ema_calendar_archive.json preserves source event IDs and titles.
archive_manifest.json records source hashes. build_archive.py regenerates
the embedded fragment after an intentional source-calendar update.

Study interpretation
This is an independent-observation indicator, not a portfolio order system.
The entry reference is the historical pre-release close. Alerts fire at its
confirmed closing update, when the release is due; this does not guarantee
an executable pre-release fill. Spread, commissions and slippage are absent.
MFE/MAE ratios describe price paths, not realized profit or profit factor.

The lookback start is anchored when the script fully calculates. Reloading
advances that start. New live events remain eligible while it stays loaded.
The tables disclose the start and observed chart/calendar coverage. Price
history depends on TradingView's loaded bars; unavailable bars are not added.

Validation
validate.py is an independent standard-library Python oracle. It can use the
archived audited TradingView calendar and native 6E price history from the
prior study, or reconstruct the new indicator's observations from its CSV.

Run from the repository root:
python3 forex_news/news_ema_move_checks/validate.py
python3 forex_news/news_ema_move_checks/validate.py --native-export PATH

The native export must include News entry side, News measured side, News
event timestamp and the new 15-minute EMA plots. Download chart data from
TradingView after loading the relevant price history. This checks source
calendar timing separately from MAE/MFE arithmetic; agreement in table math
alone does not prove the historical release dates are correct.

Final native check on October 17, 2026
TradingView compiled and saved the final source, which was read back exactly.
The full native export contains 20,908 bars and 57 selected entries. All 57
timestamps and directions match the audited archive; 1,140 horizon fields
match the independent oracle. Both EMA plots exactly match the original
EMA Cloud Stats export wherever the original plot values are available.
At H5 (75 continuous minutes): average MFE 25.83 pips, MAE 14.55 pips,
directional close +10.09 pips, favorable close 59.6%, MFE/MAE 1.775x.
These are descriptive, cost-free observations, not executable returns.
verification.json and news_ema_move_applied.jpg preserve the final evidence.

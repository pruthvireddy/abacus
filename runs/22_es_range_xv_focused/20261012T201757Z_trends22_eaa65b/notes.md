# Decisions and inspection history

## 2026-10-12 — initialize the focused ES module

The user requested a new study module for ES Range XV, with yearly results and
the seven specified session/timeframe breakdowns for all future statistics.
Initialize study 22 without inventing an event, statistic or research outcome.
Implement the reporting helper and a read-only scope description.

Use New York time, consistent with the existing enhanced exports. Interpret
19.30, 9.30 and similar notation as 19:30, 09:30, etc. Boundaries include the
start and exclude the end. Base-bar membership uses opening time; future
event-based metrics must declare causal grouping time before execution.

Use inferred trading-session year from `session_date_proxy`, keeping overnight
windows within the existing 18:00-rollover convention. Preserve overlaps and
all-hours observations outside the named windows. Require yearly-by-window
tables as well as separate annual and all-years window sections.

The user has not selected one Range XV setting. Pin ES 4/5/6 separately from
the long-history snapshot; selecting the first analysis universe remains part
of the next metric specification. Available OHLC and absent volume were inspected
earlier in this chat. Coverage, column names and manifest inventory were reviewed;
no new statistical outcomes or feature selection were examined for this study.
Other Range XV studies already exist; future predictive claims must disclose
relevant prior inspection instead of asserting the whole history is untouched.

`study.yaml` deliberately uses JSON syntax, valid YAML 1.2, to avoid adding a
parser dependency to the locked workspace. Study 22 owns its helper/tests and
is registered in the existing verification registry. No completed run exists.

## 2026-10-12 — authorize trend-length analysis and Vercel publication

The user explicitly requested overall statistics as well as annual/session
breakdowns, the first directional trend-length analysis for all three settings,
and a final study webpage with chart tabs visible on Vercel. This authorizes the
local analysis, verified sealing, selected publication and production release.

Before viewing outcomes, freeze protocol 0.2.0: exact candle close-open sign,
doji breakers, completion-proxy population, no cross-session stitching, unknown
starts/ends censored, full final partial session excluded. Group by first-candle
start time; do not cut trends at named windows. Preserve all original rows,
including identical timestamp/OHLC rows, with flags rather than speculative
removal. Require independent source reconstruction and all-cell summary checks.

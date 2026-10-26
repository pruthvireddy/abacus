# Asia session VP — previous-session profile extension 1.1.0

Prepared 2026-09-29 as an additional, exploratory investigation after the
[1.0.0 report](../../runs/14_asia_session_vp_levels/20260929T124500Z_asiavp_b2/report.html)
was inspected. That completed run and the [1.0.0 protocol](protocol-1.0.0.md)
remain unchanged. These two added hypotheses do **not** have a previously
untouched 2024–2025 validation or 2026 check.

## Input and clock

Use the pinned `nq_causal_vp_hvn__1.0.0` release in `inputs.lock.json`.
"Previous day" means the last completed **RTH profile (09:30–16:00 New York)**,
saved as `rth_vah`, `rth_poc`, and `rth_val` on each evening minute. It does not
mean a full 18:00–17:00 futures-session volume profile; that series is not in
this release. The saved levels are fixed during the following evening. Each
signal compares the current minute's range and close with the pre-bar level
snapshot, built only from completed earlier bars. Historical selected-contract
unadjusted coordinates are primary. No adjusted-coordinate sensitivity is
claimed here.

Signals can use the 18:00–20:00 interval to arm a breakout, but the entry must
be the next contiguous one-minute open during `[20:00, 00:00)` New York.
Pre-entry prices are excluded from outcomes. Include the entry candle in each
5, 10, and 20 complete one-minute-bar horizon; require the full contiguous path
to close by midnight. Save excluded candidates and censored paths separately.

## D. Previous-RTH POC approach fade

The primary working interpretation of *fade* is to oppose the approach to the
fixed previous-RTH POC. If the preceding close is above POC and a later candle
range intersects POC ±1 tick, enter **long** at the next open. If it approaches
from below, enter **short**. Do not infer a touch merely from a gap across a
level: the candle range must intersect it. Count only the first in-window
contact from each approach side per futures session; retain later contacts in
the signal ledger if this definition is revisited. A rejection close is not
required in the primary case. There is no approach-distance/ATR filter.

This direction is an explicit interpretation of the user's request, not a
claim that the user separately confirmed the side mapping. If corrected,
freeze a changed protocol and make a new run before inspecting corrected
outcomes.

## E. Previous-RTH VAH/VAL breakout, retest, continuation

An upper breakout occurs when a candle closes at least 1 tick above the fixed
previous-RTH VAH, with its preceding close not already above that same level.
On a later candle within 60 elapsed minutes, require approach from above,
a range intersection with VAH ±1 tick, and a close at or above VAH. Enter
**long** at the next open. Mirror the rule at VAL: break below, retest from
below, close at or below VAL, then enter **short**. A retest that closes more
than 1 tick back inside value cancels the arm. An opposite breakout cancels
and can replace an old arm. A same-candle breakout/retest cannot qualify.
Track arms, failures, expiry, outside-window triggers and accepted entries.

## Outcomes and interpretation

For each accepted entry and each horizon, long MFE/MAE are the positive parts
of maximum high minus entry / entry minus minimum low; short signs reverse.
The terminal close delta is `direction × (last close − entry)`, so positive is
favorable for either side. Report means in NQ points and in units of the mean
one-minute true range over 60 completed pre-signal minutes (`TR60`). This is
not conventional 14-bar ATR. Also report sample count, distinct sessions and
weeks, favorable-terminal share, and two-week moving-week uncertainty interval
for average signed close delta. A zero or unavailable TR60 yields null
normalized values with its own denominator, never zero-filled.

Retrospective quality eligibility requires the release's prior-reference
completeness, same-contract cleanliness, and nondegraded flags. This is
conservative because those flags cover the whole prior-reference set, not just
RTH. Missing future minutes, a contract change, and future degraded bars
censor only the affected horizon. Splits follow protocol 1.0.0: 2010–2019
historical context, 2020–2023 development, 2024–2025 previously inspected
validation years, and 2026 YTD. All are descriptive for these added setups.
MAE/MFE are hypothetical excursions, not realized trading P&L. No costs,
slippage, fill model, or net edge is established.

The earlier three setups and their sealed evidence remain available in the
1.0.0 run; this extension evaluates D and E separately rather than silently
changing A–C's established cohorts or horizon denominators.

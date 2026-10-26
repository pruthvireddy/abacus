# Practice, chartless reading and heatmap interpretation

Seven exported transcripts were read in full. Their exact first/last timestamp
coverage is in the media ledger. Reading all exported captions does not establish
that every spoken word of a longer lesson was available. The two chartless
exports end at 02:55 and 02:52; the article slide and the separately identified
Jigsaw written material supply additional context. These are curated third-party
lessons, principally PriceSquawk, Jigsaw/Peter Davies and Bookmap.

## Chartless reading changes the representation

[Part 1, 00:24–02:55](https://www.youtube.com/watch?v=5bpUm4_JYX0&t=24s)
describes reducing the problem to possible positioning, trapped participants
and favorable location/risk. Davies says existing effective chart methods
need not be discarded. His comments about prop-firm training speed are
anecdotes, not independently established educational outcomes.

[Part 2, 00:13–02:52](https://www.youtube.com/watch?v=4rdT4X6-_wc&t=13s)
prefers a retracement after a reversal to the exact reversal itself. It compares
the current swing sizes with a new move, while giving profile structure more
weight than a fixed measured-move rule. The 10/7 tick example is illustrative.
How closely a volume boundary holds depends on the instrument's liquidity;
a poke through it is not necessarily decisive. See also the actually inspected
[source slide](chart-cases.md#c07--the-chartless-trading-slide).

## The heatmap is a history of displayed depth

The [short explanation, 00:03–00:56](https://www.youtube.com/watch?v=NFbiSX6PYXo)
and [detailed explanation, 00:05–03:04](https://www.youtube.com/watch?v=8AaFSdjsZbY)
describe translating current order-book quantities into colors, then retaining
that history alongside price and traded volume. Addition, withdrawal and actual
transaction are distinct observations. Displayed depth is not a trade commitment.

A particularly useful qualification appears at
[02:20](https://www.youtube.com/watch?v=8AaFSdjsZbY&t=140s): the displayed color
scale is relative to the largest depth within the visible range. Zooming can
change an area's color without changing its recorded quantity. Compare actual
quantities/tooltips, not a remembered shade. This makes a bright band a candidate
location to investigate, not an automatic support/resistance signal or fixed
liquidity threshold.

## Three drills train three different skills

| Lesson | Training object | What to review |
|---|---|---|
| [Trading Naked, 00:03–15:25](https://www.youtube.com/watch?v=h7XwWBqSadI) | Observe DOM aggression and work resting bids/offers in simulation, with a basic profile | Overlay fills on a one-minute volume chart afterward; look for repeated wrong-side attempts, premature entries and uncontrolled flipping |
| [Flip a Coin, 00:00–04:01](https://www.youtube.com/watch?v=kbgArYutC9s) | Take an externally assigned directional premise for a limited window; practice location and management rather than direction forecasting | Do not enter blindly at the start; record how a good fill, scratch or small controlled loss followed the instructions |
| [Trade Like a Machine, 00:00–15:43](https://www.youtube.com/watch?v=zCyqylqgrT0) | Follow a declared rule set across volume contexts without improvising each trade | Assess adherence separately from P&L; the instructor explicitly says the default strategy need not make money |

Trading Naked's retrospective review identifies repeated shorts in an up move
and suggests stepping back after repeated attempts
([07:31–09:36](https://www.youtube.com/watch?v=h7XwWBqSadI&t=451s),
[13:18–13:48](https://www.youtube.com/watch?v=h7XwWBqSadI&t=798s)).
The exact retry count belongs to that exercise, distinct from Vern's day-level
stop and FT71's setup-level stopping rule.

Trade Like a Machine uses the **last completed** one-minute volume observation
to select a low/normal/high context
([01:14](https://www.youtube.com/watch?v=zCyqylqgrT0&t=74s),
[12:51](https://www.youtube.com/watch?v=zCyqylqgrT0&t=771s)).
It illustrates ranges in low volume and pullbacks in normal volume, while
allowing no trade in high volume. Its rough 60/180-contract audio thresholds
are examples for the demonstrated instrument/period, not portable settings.

All three drills are exercises in controlled observation and execution.
Their demonstrations and promotional statements do not establish net edge,
realistic queue fills or readiness for live risk. This knowledge base proposes
practice records; it has not run the drills or changed any trading account.

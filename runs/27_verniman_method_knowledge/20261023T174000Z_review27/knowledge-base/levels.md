# Level selection: role, context, response

Primary sources: [Trading Plan](topics/t01-the-trading-plan.md),
[Glossary](topics/t02-glossary-terms.md),
[Trading Value](topics/t18-trading-value.md),
[Value Transition](topics/t16-value-transition.md), and
[actual chart cases](chart-cases.md). This framework is Abacus's organization
of those sources. It does not recover a proprietary drawing algorithm.

## Draw a market map before a trade trigger

Vern's stated preparation begins with the larger auction, yesterday and
overnight. Accordingly, a useful annotation must name its reference period:
for example, yesterday's RTH POC, overnight high, developing intraday HVN or
a multi-session auction boundary. An unlabeled POC is ambiguous. Distinguish
a level known before the open from one that only develops later.

The same price may have several roles, but those roles should be stated
separately. A prior high identifies a test; a local volume edge may make a
favorable entry location; another accepted area supplies a destination. The
existence of three marks does not prove three independent confirmations.

## What each family contributes

| Family | Source meaning | Useful question | What the sources leave open |
|---|---|---|---|
| POC / VPOC | Price with the largest activity in the selected profile; T16 explicitly uses volume | Where has the chosen auction concentrated trade? | Session anchor, aggregation, tie handling and treatment of developing versus final profiles |
| HVN | A relatively high-volume region | Where is activity being accepted, and is it a destination or an area to manage around? | Exact node segmentation, width and persistence |
| LVN | A relatively thin part of the distribution | Does this boundary reject exploration or give way to new acceptance? | Quantitative thinness, minimum contrast and permissible penetration |
| HVE | Edge of a fuller-volume range | Does the transition between acceptance and thin trade provide a useful structural reference? | How the edge is computed and the tick buffer |
| VAH / VAL | Boundaries of a defined value area | Is the market inside, outside, returning to or establishing value elsewhere? | Profile type, value-area algorithm, percentage, session and re-entry condition |
| Overnight / prior-day highs and lows | Extremes of named reference periods | Which prior boundary is being tested, and how does the opening relate to it? | Feed/session definitions and what counts as a successful test |
| LIS | A selected dividing level for bullish/bearish scenarios | Which side supports which scenario, subject to the response? | The unique selection algorithm and handling of conflicting references |
| PBT | Projected completion of a balanced, symmetric distribution | Where might the auction find a balancing destination? | The projection formula, anchor, width and failure criterion |
| MID / OSR / IB | Midpoint, initial opening swing and first-hour range references | What does current action imply relative to a named early auction? | OSR's exact swing detector; which range supplies MID; operational breakout/retest rules |
| GAP / SOC | Opening-versus-prior-close separation; origin of a news impulse | Does an earlier discontinuity or impulse origin remain relevant to the present scenario? | Exact price convention and probability/availability of a revisit |

TPO/time-based profile and volume profile are related representations but are
not interchangeable measurements. A volume POC is not automatically a TPO POC;
a low-volume tail does not prove a single-print tail. The glossary's compact
language must be expanded by stating the actual data representation.

## What to do with a level after drawing it

In a stable balance, Vern describes looking for favorable prices around its
extremes and accepted value as a destination. In a directional value transition,
he looks for contextual pullbacks rather than fading an ongoing move. This is
conditional mode selection, not the instruction to buy every low-volume node.

At the selected location, record what would support rejection or acceptance.
Some relevant observations in the curated lessons are aggressive volume that
fails to advance, replenishing displayed liquidity during execution, changes
in price progress, building volume away from the old center, and correlated
activity. None has a universal threshold declared across this corpus. A single
large print, one POC shift or a bright band cannot settle the question alone.

An LVN can lose its former role when activity fills it in or sustained trade
develops beyond it. Its historical label is not a perpetual order instruction.
Similarly, a former POC may remain a useful reference without being today's
active center. See the cross-author distinctions in
[the VPOC review](video-value-transition.md) and
[Mitchell's contextual examples](video-auction-mitchell.md).

## An annotation record worth saving

The following is an original documentation template, not Vern's supplied form:

```text
Level ID / price or zone:
Role: location / destination / scenario divider / invalidation reference
Instrument and actual contract:
Source: RTH / overnight / composite / developing local auction
Calculation or drawing convention:
First available timestamp:
Current state: balance / exploration / new acceptance / unresolved
Scenario supported if:
Observation that would reject that scenario:
Next destination and intervening structure:
Image or replay timestamp supporting the observation:
```

This makes a discretionary mark reviewable. It does not eliminate discretion.
If the source does not tell us the drawing convention, write “not recovered”
instead of substituting a plausible indicator setting.

## What has actually been recovered about Vern's drawings

The reviewed charts show labeled volume edges, thin areas, gaps, conditional
arrows and destinations. They support the roles above and demonstrate distinct
location/target areas. They do **not** identify one deterministic rule that
would reproduce his daily LIS, every HVE or PBT from unseen data. Reconstructing
such a rule would require additional contemporaneous examples and a separately
specified research protocol, with availability and annotation revisions tracked.

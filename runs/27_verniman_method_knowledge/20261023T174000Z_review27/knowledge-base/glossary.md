# Working glossary

Acronym expansions follow the selected [Glossary Terms article](https://verniman.blogspot.com/2014/04/glossary-of-terms.html)
unless another source is named. The auction-state explanations (acceptance,
rejection, balance, imbalance and transition) are Abacus synthesis of
[Auction Theory](topics/t03-auction-theory.md),
[Value Transition](topics/t16-value-transition.md) and
[Trading Value](topics/t18-trading-value.md), not extra definitions silently
attributed to T02. “Meaning here” is deliberate: acronyms may have
different meanings in other literature or software. The table explains the
source language without endorsing its statistical claims.

## Auction and structure

| Term | Meaning here | Qualification for use |
|---|---|---|
| Acceptance | Activity accumulates around a perceived value area | Observed volume/time does not identify participants' private beliefs or remaining positions |
| Rejection | Exploration fails to develop sustained activity and turns away | The corpus supplies no one universal time/volume threshold |
| Balance | Rotation around an established region of activity | A contextual state; not a promise of reversion |
| Imbalance | Directional exploration away from established value | Can fail or develop new acceptance |
| Value transition | Development/migration of accepted activity to another region | T16 distinguishes price moving first from volume confirming later |
| POC | Point of Control of the specified profile | Name the profile type and session; the generic term is underspecified |
| VPOC | Volume Point of Control: maximum-volume price in the selected profile | Developing and final VPOCs are different information states |
| HVN | High Volume Node: a fuller activity region | A region can be wider than the modal price; not every HVN is the POC |
| LVN | Low Volume Node: relatively thin activity | Thinness is relative to an explicitly chosen distribution |
| HVE | High Volume Edge: upper/lower boundary of a fuller-volume region | A boundary role; no exact detector is recovered |
| VAH / VAL | Value Area High / Low | Require a chosen construction algorithm and session |
| Excess | The article's sign of a forceful auction ending, described through a tail | T15's prose uses single prints while its chart uses volume; distinguish the measures |
| Single print | A time/profile structural description used by the excess article | Cannot be verified merely from a volume histogram |
| Double distribution | Two fuller regions separated by thinner activity | Useful shape description; does not alone establish trade direction or live timing |

## Vern's scenario vocabulary

| Term | Meaning here | Qualification for use |
|---|---|---|
| PBT | Projected Balance Target: a proposed symmetric distribution completion | Projection construction is not specified sufficiently for exact reproduction |
| LIS | Line in the Sand: bull/bear dividing reference | Scenario split, subject to context; not a guaranteed turn |
| BTV | Back to Value: balance returning toward accepted activity/POC | The article's 70% assertion is unverified |
| VAR | Value Area Rule: return into prior value followed by a proposed rotation across it | Means this rule here; its 80% claim is not Abacus evidence |
| SOC | Scene of Crime: origin of a news-driven impulse | Possible revisit reference; no inevitability established |
| 1TF | One Tick Failure: marginal test of an extreme followed by opposite pressure | The blog's explicit expansion; do not silently reinterpret the acronym |
| OSR | Opening Swing Range: first high and low of the initial post-open auction | Not automatically the first five-minute or first-hour range |
| MID | Midpoint of the relevant initial auction range | State which range and when its endpoints became available |
| GAP | Today's opening versus yesterday's closing reference in the glossary | The exact closing-price convention is needed before measurement |
| SOH | Sit On Hands | A valid no-trade state when action is erratic or incoherent |
| OTF | Other Time Frame: beyond intraday, such as daily/weekly/monthly | Source framework for different horizons; not proof of participant identity |
| IVR | Implied Volatility Range | Source describes price × volatility × square root of horizon; units and scaling are not fully specified |
| MFE | **Maximum Favorable Extension** in this glossary | Source relates the current range to IVR; do not substitute another P&L metric with the same acronym |
| CLVN | Label visible on one excess chart | Not expanded in the selected glossary; its meaning is not asserted here |

## Session and price references

| Term | Meaning here | Qualification for use |
|---|---|---|
| RTH | Regular Trading Hours | Vern's trade windows are subsets of the session, not its full definition |
| ETH | Electronic Trading Hours | Do not automatically equate the full electronic session with the overnight-only window |
| IB | Initial Balance | Statistics article refers to the first-hour range; specify its exact session anchor |
| ONH / ONL | Overnight High / Low | Need the precise overnight window |
| HOD / LOD | High / Low of Day | A developing reference changes as new extremes form |
| YHOD / YLOD | Yesterday's High / Low | Choose the relevant session, contract and clock |
| YVAH / YVAL / YPOC | Yesterday's value boundaries and POC | Preserve their actual construction; not today's developing profile |
| ATH | All Time High | Requires a contract/series definition; adjusted continuous and actual contract highs can differ |
| EOD | End of Day | A time reference, not one universally specified timestamp |
| MOC | Market-on-Close order | Source's close-related order context; no current exchange-order specification is inferred |
| 1SD | One Standard Deviation | A dispersion measure; a profile is not proven Gaussian because it looks like a bell |

## Order flow and execution

These explanations organize the reviewed Jigsaw, FT71 and Bookmap material.
They supplement rather than silently extend the blog's glossary.

| Term | Working meaning | Essential distinction |
|---|---|---|
| DOM / ladder | Current displayed bids and offers across prices | Displayed intent can change before execution |
| Time and sales / tape | Stream of executed transactions | A stream of prints is not the current resting order book |
| Aggression | Orders executing against resting liquidity | Equal matched buy/sell volume can still differ in aggressor classification |
| Delta / CVD | Aggressor-classified buying minus selling, accumulated using a stated convention | Check sign, reset and classification; not exchange open interest |
| Absorption | Executed pressure repeatedly meets liquidity without corresponding price progress | An interpretation requiring activity plus response; not “large size” alone |
| Replenishment | Displayed liquidity reappears while transactions occur | Suggestive of defense; identity and hidden inventory remain unknown |
| Heatmap | Historical display of recorded order-book depth | Color depends on scale/viewport; depth differs from executed volume |
| Magnet | A candidate auction destination | A scenario term, not a guaranteed future print |
| Structural invalidation | Observation/location where the trade premise fails | Distinct from choosing an arbitrary monetary stop distance |
| Scratch | Exit near the entry price in the discussed execution context | Costs and slippage can make nominal breakeven a loss |
| Scaling | Adjusting position size through multiple entries/exits | Evaluate the whole position and costs; one profitable scale does not erase remaining risk |
| Expectancy | Mean net result under a specified trade policy | Touch probability and win rate alone cannot establish it |
| MFE / MAE in FT71's lessons | Maximum favorable/adverse excursion of a trade or campaign | Different from Vern's IVR-based Maximum Favorable Extension; some analyzer examples use aggregate contract-ticks, so state units and campaign boundaries |

For operational detail and timestamped sources, use the
[execution review](video-execution.md), [Bookmap course](bookmap-course.md),
[FT71 management](video-ft71-risk-management.md),
[different scalping horizons](video-scalping.md), and
[source coverage](source-coverage.md).

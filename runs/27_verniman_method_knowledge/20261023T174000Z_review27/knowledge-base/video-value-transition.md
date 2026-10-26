# Value transition — what a POC shift tells you, and what it cannot

This review covers the two videos selected in Vern's [Value Transition](https://verniman.blogspot.com/2013/03/trading-vpoc-shifts.html) article. Their speakers are **Bob Hoffman** ([IPyP18FKvds](https://www.youtube.com/watch?v=IPyP18FKvds)) and **Bri Guy with guest Kumar** ([P9ERBei186g](https://www.youtube.com/watch?v=P9ERBei186g)). They are curated third-party teaching. Vern's article connects price discovery to subsequent volume acceptance; these videos explain some of the decisions hidden inside that abstraction.

## Exact review coverage

| Capture | Coverage read | Retained identity |
|---|---|---|
| `IPyP18FKvds.txt` | Complete English auto-generated transcript, **00:03–1:37:33**, all 2,100 lines | 92,029 bytes; SHA-256 `71b763437bf2afcb66d47d8566150b747ee9f5e7a51362787d2353acf4205c98` |
| `P9ERBei186g.txt` | Complete English auto-generated transcript, **00:06–1:58:33**, all 2,536 lines | 109,313 bytes; SHA-256 `dca0dc0c5fa2bdb52e31121b223cea6ac8beeeea8a8433202e63568d1f3ecc9f` |

No audio or video chart frames were independently inspected for this note. Explanations of displayed charts below report the speakers' descriptions. Captions repeatedly misrecognize VPOC, VWAP, names and prices. Numerical precision is limited accordingly. The latter portion of P9ERBei186g includes unrelated stock/options examples, historical brokerage promotion and closing conversation; those were read but do not become part of this value-transition framework.

## 1. Specify the profile before naming its POC

Hoffman defines VPOC as the price with the greatest traded volume within a specified frame, a statistical mode ([06:10–08:24](https://www.youtube.com/watch?v=IPyP18FKvds&t=370s)). A local volume peak can be an HVN without being the single largest peak in the entire profile. A developing VPOC changes when another price accumulates more volume. Its displayed jump may look sudden even though the transactions building the new distribution occurred gradually.

Kumar distinguishes a daily profile, a bounded multisession micro-composite and a broader composite ([06:25–11:26](https://www.youtube.com/watch?v=P9ERBei186g&t=385s), [27:40–30:00](https://www.youtube.com/watch?v=P9ERBei186g&t=1660s)). His preference for reserving an unqualified “VPOC” for the daily profile is a communication convention. It does not contradict Hoffman's use of a volume mode on any specified frame. Both require knowing which observations were aggregated.

The host's discussion of FT71's composite construction at [1:16:31–1:19:54](https://www.youtube.com/watch?v=P9ERBei186g&t=4591s) quotes a preference for selecting a market rotation rather than a fixed number of days. This is **Kumar's discussion and the host's quotation of FT71**, not a directly observed FT71 explanation in this video. Their exact composite boundaries remain discretionary.

**Abacus implication:** a level record needs a start, end/as-of time, session definition, contract/data basis and price-bin policy. “POC at X” is incomplete. Two analysts may get different levels because their profiles contain different trades, rather than because one arithmetic calculation failed.

## 2. A shift is historical acceptance information

At [20:00–26:33](https://www.youtube.com/watch?v=IPyP18FKvds&t=1200s), Hoffman carefully distinguishes value having moved from a claim that it will keep moving. The shift summarizes transactions already completed. It is a prompt to reassess context and wait for directional information, rather than an automatic continuation or reversal entry.

This explains his criticism of giving every VAH or untouched POC equal importance ([08:45–11:39](https://www.youtube.com/watch?v=IPyP18FKvds&t=525s)). A label says what was measured; its location within larger structure determines why it may matter. He also treats P-shaped and b-shaped profiles as insufficient to settle continuation versus reversal without context ([12:15–19:47](https://www.youtube.com/watch?v=IPyP18FKvds&t=735s)). He discusses differing interpretations associated with Steidlmayer and Dalton but does not establish a universal verdict on either author.

His three lenses at [26:45–35:26](https://www.youtube.com/watch?v=IPyP18FKvds&t=1605s) are:

- **Context:** where the new mode sits relative to larger areas from which price previously departed strongly.
- **Structure:** whether the migration forms a meaningful separate distribution or merely moves the mode inside an existing balance. He gives the latter little significance.
- **Mathematical relationship:** price, VWAP, VPOC and volatility. He introduces this relationship but defers a complete method; it cannot supply a recovered trading algorithm here.

## 3. Developing information must remain different from the final picture

Kumar's discussion at [1:01:27–1:04:42](https://www.youtube.com/watch?v=P9ERBei186g&t=3687s) distinguishes a dotted evolving VPOC path from the session's eventual finished profile. His intraday interpretation uses the POC available at the time, the position of price above it and a rising VWAP. The final POC is not a legitimate replacement for those earlier observations.

Separately, he uses the **previous session's** completed value area as the fixed reference when discussing today's opening location ([16:47–20:52](https://www.youtube.com/watch?v=P9ERBei186g&t=1007s)). That is different from today's developing value area. He describes an untouched prior POC as remaining extended on his chart until price revisits it ([21:14–23:15](https://www.youtube.com/watch?v=P9ERBei186g&t=1274s)). A faithful implementation would still need to define the qualifying session and what counts as a touch.

**Abacus implication:** preserve the actual developing state at each decision time. A day labeled trending after the close and a final double distribution cannot silently become facts available at the open. POC availability is as important as its price.

## 4. Balance, trend and trade location answer different questions

Vern's article describes rotation around value on a non-trending day and price leading value during directional discovery. Hoffman adds that entry exactly at the newly accepted mode does not, by itself, give him an advantageous price ([23:29–26:33](https://www.youtube.com/watch?v=IPyP18FKvds&t=1409s)). Kumar likewise says he avoids entering at VPOC because that location alone offers him no edge ([57:52–59:17](https://www.youtube.com/watch?v=P9ERBei186g&t=3472s)). He discusses VWAP reactions, other references and taking partial exits ahead of potential obstacles ([59:19–1:01:21](https://www.youtube.com/watch?v=P9ERBei186g&t=3559s)).

These statements can coexist: a POC may summarize acceptance or serve as a destination without being the preferred entry. A migration may support a continuation scenario while the next trade still needs price advantage, invalidation and confirmation. That reconciliation is Abacus synthesis; it does not prove the speakers use identical setups.

Kumar's LVN discussion includes both rejection on retest and quick travel through a low-participation area ([48:09–50:03](https://www.youtube.com/watch?v=P9ERBei186g&t=2889s)). An LVN is consequently a location at which to observe the response, not a guarantee that price must bounce or must accelerate. His retrospective certainty in some chart commentary is not a quantified probability estimate.

## 5. Two spoken examples show location before trigger

**Hoffman's P-shaped-profile example** ([36:26–51:39](https://www.youtube.com/watch?v=IPyP18FKvds&t=2186s)) combines a shifted distribution, elapsed TPO development, developing VAH near the session high, and a deep prior rotation creating room for a target. He then describes waiting for a return to a favorable upper location and a cumulative-delta divergence before considering a short. The large retracement is used to identify available trading space, rather than automatically being called weakness. The TPO-width wording alternates between five and more than five, and he says this number is not sacred; no exact threshold is adopted here.

**His footprint example** ([51:42–59:59](https://www.youtube.com/watch?v=IPyP18FKvds&t=3102s)) follows several small downward VPOC shifts that are ignored because no planned location has been reached. Near a previously identified demand area, heavy aggressive selling produces little further price movement, followed by buying from the low. The combination, rather than the VPOC shift alone, supplies his reversal idea. At [55:34–56:54](https://www.youtube.com/watch?v=IPyP18FKvds&t=3334s), he explicitly states that these are reconstructed potential setups, not trades he actually took.

At [1:08:24–1:10:09](https://www.youtube.com/watch?v=IPyP18FKvds&t=4104s), he explains his level-selection preference: strong momentum departures across multiple frames first, with low-volume nodes as corroboration. At [59:04–1:00:21](https://www.youtube.com/watch?v=IPyP18FKvds&t=3544s), he restates the sequence as context, a location known before entry, then an order-flow trigger.

His historical contract-volume quantities, reversal-bar settings and personal morning schedule are examples of his own calibration. No supplied distribution, significance test or out-of-sample record establishes them as present ES thresholds.

## 6. Keep the useful distinctions; qualify the loose terminology

- **Cumulative delta is not open interest.** Hoffman calls it real-time open interest around [49:22](https://www.youtube.com/watch?v=IPyP18FKvds&t=2962s). Treat that as loose explanatory language. His displayed measure concerns bid/offer-classified traded volume. [CME defines open interest](https://www.cmegroup.com/trading/about-volume.html) as outstanding contracts, counted once per matched long/short pair. The delta series does not identify which trades open or close positions.
- **A TPO is not the highest-time price itself.** Kumar's early wording compresses those ideas. Keep the time-price observations and the modal price derived from them separate, and distinguish that time-based POC from the volume mode.
- **A computed value area does not require normally distributed data to exist.** Hoffman's critique at [10:35–11:22](https://www.youtube.com/watch?v=IPyP18FKvds&t=635s) challenges the meaning of a bell-curve interpretation on skewed/trending profiles. It should not become a claim that a coverage algorithm cannot calculate boundaries for another shape.
- **Large volume plus little movement is evidence of a response, not participant identification.** Hoffman himself rejects separating commercial and fund contracts from his footprint at [1:20:36–1:21:35](https://www.youtube.com/watch?v=IPyP18FKvds&t=4836s). Avoid turning an absorption interpretation into proof of a named institution or known remaining position.
- **Session choices differ.** Kumar prefers separate RTH context with selected overnight references; Hoffman discusses continuing cumulative delta across RTH and overnight ([1:13:45–1:15:15](https://www.youtube.com/watch?v=IPyP18FKvds&t=4425s)). These are different analytical configurations, not one merged rule.

## What remains unresolved

Neither transcript supplies a complete reproducible set of tie handling, price bins, composite selection, profile readiness, causal trend classification, accepted shift distance, exact trigger, stop, costs and target rules. The spoken examples are selected illustrations. Their actual chart scales, timestamps, numbers and intrabar sequence require a separate frame/data review. Historical software features, prices, broker promotions and course availability are not current recommendations.

For future research, the sharp question is not simply whether POC moved. It is whether a **specified, causally available** migration at a **previously defined location**, followed by a **specified response**, changes attainable outcomes after risk and costs. This knowledge base has not performed that test.

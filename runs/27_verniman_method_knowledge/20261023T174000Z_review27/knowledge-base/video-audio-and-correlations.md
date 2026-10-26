# Audio order-flow alerts and intermarket context

These five embedded videos supply much of the teaching behind Vern's [Order Flow Alerts](https://verniman.blogspot.com/2013/09/squawk-box-audio.html), [Using Order Flow](https://verniman.blogspot.com/2013/07/trade-market-value.html) and [About Correlations](https://verniman.blogspot.com/2017/01/markets-correlation.html) pages. Four are historical Tickstrike/PivotFarm presentations by Amar, including hosted promotional webinars. The fifth is a Jigsaw presentation about reading correlated markets; the retrieved captions do not securely identify its speaker by name. These are third-party explanations curated by Vern, rather than a transcript of Vern's own live execution.

## Exact coverage

Every retained caption line was read, including introductions, questions, closing material and commercial offers. These are English auto-generated captions. **Audio and video chart frames were not independently inspected.** Chart examples below describe the speakers' narration; they are not verified chart reconstructions or execution records.

| Video | Complete retrieved caption range | Lines / bytes | SHA-256 |
|---|---|---|---|
| [PdTeg3atlEo](https://www.youtube.com/watch?v=PdTeg3atlEo) | 00:00–12:33 | 379 / 13,761 | `bc4e64a590cb315ec0d70a1c5e9990ccb2e94ff41fae4c56807770de055a29c3` |
| [qGBZkTsoKQg](https://www.youtube.com/watch?v=qGBZkTsoKQg) | 00:00–37:34 | 921 / 40,745 | `c07ac94f62189ac8b6e4569d97919e64c73889ec9689e2b0e90625194f2ca8f8` |
| [\_\_72lXKGtRs](https://www.youtube.com/watch?v=__72lXKGtRs) | 00:00–51:24 | 1,174 / 52,285 | `5466bb10cf7a1ceedc8c082da2d021822ec92ef4d8849b1dca8f8f68b4ede442` |
| [8BVb2DI3jic](https://www.youtube.com/watch?v=8BVb2DI3jic) | 00:00–1:24:56 | 2,471 / 98,466 | `d5aa7bd193d770f90e7b49e2a54f0e9bfe046934a5ebdbe7e64267e2b02f152a` |
| [t5B2N2xathw](https://www.youtube.com/watch?v=t5B2N2xathw) | 00:00–59:01 | 1,494 / 67,674 | `8f3c5717c6369a585334db9fc1306941890c2e61421b399352bfcc3ed76549fa` |

The `qGB` capture ends during commercial discussion; its retained endpoint does not prove that the entire original video has captions. The older TradingPub webinar has a technical interruption around 13:27–15:15. Neither gap is reconstructed. Price numerals and names are sometimes malformed in captions.

## 1. Sound directs attention to unusual activity

Amar presents audio as another way to notice transaction activity while looking at a chart or monitoring several instruments. It can draw attention to a change in activity without requiring continuous inspection of every tape. It does not select a strategy by itself ([PdTeg, 01:40–03:59](https://www.youtube.com/watch?v=PdTeg3atlEo&t=100s); [qGB, 09:22–11:18](https://www.youtube.com/watch?v=qGBZkTsoKQg&t=562s)).

The same burst has several possible interpretations: initiation at a breakout, confirmation of an existing direction, a reason to keep managing a position, or terminal activity after an extended move. Amar explicitly distinguishes a momentum burst from a capitulation burst using what happened beforehand ([qGB, 13:18–13:59](https://www.youtube.com/watch?v=qGBZkTsoKQg&t=798s)). The short presentation lists correlation, momentum, breakout, confirmation, capitulation, management, divergence and post-news activity as uses, not as a single sequence of required entries ([PdTeg, 03:03–03:59](https://www.youtube.com/watch?v=PdTeg3atlEo&t=183s)).

**Abacus synthesis:** the useful abstraction is **location and prior auction → unusual activity → observed price response → action under the trade plan**. A sound alone does not distinguish continuation from exhaustion. Calling a burst capitulation also does not prove that all trapped participants have liquidated or that reversal must follow.

## 2. A meter score is a transformation, not contract quantity

In [qGB, 19:09–21:12](https://www.youtube.com/watch?v=qGBZkTsoKQg&t=1149s), Amar says the algorithm adapts to recent conditions; a fixed absolute-contract mapping was not useful to him. High nighttime scores can accompany much less absolute volume than the same score during the active session. The later hosted webinar describes relative directional rate and size ([8BV, 06:24–07:26](https://www.youtube.com/watch?v=8BVb2DI3jic&t=384s), [42:30–43:19](https://www.youtube.com/watch?v=8BVb2DI3jic&t=2550s)). The precise formula, sample window, aggressor classification and normalization are not disclosed in these captions.

Version and display semantics matter:

- The older webinar describes a 1–10 scale ([\_\_72, 32:53–33:55](https://www.youtube.com/watch?v=__72lXKGtRs&t=1973s)). The later version adds five **lower score thresholds**, providing greater sensitivity to smaller activity changes: its level 6 corresponds to the old level 1, according to Amar ([8BV, 15:30–16:23](https://www.youtube.com/watch?v=8BVb2DI3jic&t=930s)). Therefore “level 6” has no stable cross-version meaning.
- A gray displayed score can be a recent alert retained on screen, rather than current live activity ([8BV, 47:06–47:32](https://www.youtube.com/watch?v=8BVb2DI3jic&t=2826s)).
- Audible thresholds differ from visible activity. Amar and the host use different personal settings; silence can mean the sound threshold was not crossed ([8BV, 52:13–54:42](https://www.youtube.com/watch?v=8BVb2DI3jic&t=3133s)). These settings are examples, not Vern's prescriptions.
- Each instrument's meter is processed separately; a combined multi-instrument condition was described as a future feature ([8BV, 41:18–42:04](https://www.youtube.com/watch?v=8BVb2DI3jic&t=2478s)).

A directional alert is also not a literal count of “more buyers than sellers.” Every completed trade has both sides. The webinar's audience guesses about percentages of sellers from a downward candle are illustrations, not measured trader counts ([\_\_72, 09:13–13:27](https://www.youtube.com/watch?v=__72lXKGtRs&t=553s)). Aggressive selling, traded volume, participant identity and open/close position intent are different concepts.

## 3. Filled orders, resting orders and synthetic internals are different evidence

Amar distinguishes filled transactions from the DOM's displayed intentions. Resting orders can be canceled, while the executed flow shows actual trades ([\_\_72, 16:20–19:06](https://www.youtube.com/watch?v=__72lXKGtRs&t=980s)). He explicitly says the alert tool uses **filled orders**, not resting DOM orders, and cannot identify spoofing from those absent resting-order observations ([34:13–34:27](https://www.youtube.com/watch?v=__72lXKGtRs&t=2053s), [48:07–48:20](https://www.youtube.com/watch?v=__72lXKGtRs&t=2887s)). That makes audio alerts different from a liquidity heatmap.

Not every supported input is an exchange transaction stream. Amar describes FX/Bitcoin feeds aggregated from multiple brokers; that is not a consolidated global order book. TICK, TICKQ and VIX-style internal indicators are experimental transformations without their own literal buy/sell order flow ([PdTeg, 00:35–01:38](https://www.youtube.com/watch?v=PdTeg3atlEo&t=35s); [8BV, 18:07–19:18](https://www.youtube.com/watch?v=8BVb2DI3jic&t=1087s), [21:49–22:30](https://www.youtube.com/watch?v=8BVb2DI3jic&t=1309s)). VIX and a traded volatility-futures contract must not be conflated.

Hand-drawn support/resistance rectangles in the older webinar are the presenter's annotations, not automatically generated output ([\_\_72, 26:01–26:21](https://www.youtube.com/watch?v=__72lXKGtRs&t=1561s)). Historical slides also use a separate charting platform behind the alert console ([8BV, 03:56–04:40](https://www.youtube.com/watch?v=8BVb2DI3jic&t=236s)). Do not infer an integrated chart, order-entry engine or replay capability from that visual arrangement. Replay and several other features are described as absent or planned, rather than demonstrated deliverables ([8BV, 55:48–57:45](https://www.youtube.com/watch?v=8BVb2DI3jic&t=3348s)).

## 4. Intermarket agreement supplies context, rather than a permanent leader

Amar's examples compare ES, NQ and Dow futures and, separately, NQ with several large constituent stocks. A new NQ high without corresponding strength in those stocks is treated as a reason to question its follow-through ([PdTeg, 08:02–10:41](https://www.youtube.com/watch?v=PdTeg3atlEo&t=482s); [8BV, 24:50–26:24](https://www.youtube.com/watch?v=8BVb2DI3jic&t=1490s)). His stated stock-index weights vary between presentations and refer to their historical composition. They are not current verified weights or a permanent constituent list.

The Jigsaw presentation supplies the sharper qualification: correlations change across long-term regimes and also across minutes or hours ([t5, 06:37–08:02](https://www.youtube.com/watch?v=t5B2N2xathw&t=397s)). The presenter explicitly rejects “NQ always leads ES” ([10:09–11:03](https://www.youtube.com/watch?v=t5B2N2xathw&t=609s), [56:55–57:28](https://www.youtube.com/watch?v=t5B2N2xathw&t=3415s)). A thinner market can show a larger price move from common activity, while a thicker market shows one-sided transactions before much price displacement. That is not proof that the thinner instrument initiated the move.

Here “correlation” usually means a discretionary reading of local agreement or disagreement, **not** a computed coefficient. A useful interpretation is whether related markets currently support the proposed direction and regime. Several correlated confirmations are not independent votes. Neither narrated examples nor vendor claims that stock alerts lead NQ establish a causal or reliably exploitable lead–lag relationship after latency, transaction costs and missed fills.

## 5. Read the current lean from a meaningful baseline

The Jigsaw presenter resets/recenters the compared DOMs and clears recent trades on entry so that movement and activity can be evaluated relative to that same decision moment ([t5, 19:44–21:16](https://www.youtube.com/watch?v=t5B2N2xathw&t=1184s)). This is an observational baseline, not a new support/resistance level. Automatic recentering can destroy that comparison ([47:54–48:16](https://www.youtube.com/watch?v=t5B2N2xathw&t=2874s)).

He compares both price excursion and one-sided executions. A thick market can remain near the baseline despite substantial activity; a thin market can move several ticks under the same broad pressure ([21:21–24:39](https://www.youtube.com/watch?v=t5B2N2xathw&t=1281s)). Equal tick distances across products are therefore not equivalent strength measurements. His examples are qualitative; no conversion ratio, stable cutoff or normalized cross-contract model is supplied.

He calls aligned direction a short-term safety net but explicitly says it is **neither a stop loss nor a setup** ([16:43–18:59](https://www.youtube.com/watch?v=t5B2N2xathw&t=1003s)). If all related indices are pressing down, a planned support buy may warrant waiting until that pressure becomes neutral or turns. Conversely, a small pullback in one volatile instrument need not invalidate a trade when the broader lean remains supportive ([24:41–25:20](https://www.youtube.com/watch?v=t5B2N2xathw&t=1481s)).

His narrated examples use very short charts, including ten-second views, to assess the local action relevant to a scalp ([27:06–28:19](https://www.youtube.com/watch?v=t5B2N2xathw&t=1626s); [50:46–51:44](https://www.youtube.com/watch?v=t5B2N2xathw&t=3046s)). Those observation windows belong to this presenter and purpose, rather than a universal timeframe for Vern's complete method.

## 6. Agreement can alter entry, management or regime assessment

The Jigsaw examples illustrate three distinct applications:

1. **Delay an entry:** wait when related markets actively oppose it; enter after pressure eases or obtain a better price on a local pullback. This is different from chasing a leader.
2. **Manage an existing trade:** compare the current lean with the original hypothesis. A small ordinary joint pullback is not automatically a reversal. Strength, participation and the traded market's own response matter ([t5, 29:39–31:58](https://www.youtube.com/watch?v=t5B2N2xathw&t=1779s)). In a slower European-index example, stalled price plus adverse turns in inversely related rates motivate an exit ([35:20–37:48](https://www.youtube.com/watch?v=t5B2N2xathw&t=2120s)).
3. **Recognize a possible state change:** Dow and NQ disagreement suggests choppier ES conditions to the speaker; renewed local synchronization can precede more directional follow-through, even when the chart still looks messy ([37:50–43:54](https://www.youtube.com/watch?v=t5B2N2xathw&t=2270s)). These are experience-based claims, not measured transition probabilities. He rejects an example range trade when the available room is too small ([39:29–41:14](https://www.youtube.com/watch?v=t5B2N2xathw&t=2369s)). Context does not override trade economics.

Inverse relationships require interpreting the sign correctly. His Bund/Bobl versus European-equity example is conditional on that episode, not a permanent stock/bond law ([32:04–35:18](https://www.youtube.com/watch?v=t5B2N2xathw&t=1924s)). He says violent news events and the first minutes after FOMC can make the usual comparison unhelpful; region-specific news can separately disrupt overnight US/European relationships ([46:40–47:23](https://www.youtube.com/watch?v=t5B2N2xathw&t=2800s), [49:09–49:58](https://www.youtube.com/watch?v=t5B2N2xathw&t=2949s)).

## What the combined sources support, and what remains unknown

They support attending to changes in executed activity, interpreting those changes at a price/location, comparing related markets at the intended horizon, and revising an auction hypothesis when the observable response contradicts it. They do not supply a reproducible unified entry algorithm.

Historical differences must remain visible. The older vendor says after-hours futures activity may be inadequate for his use ([\_\_72, 43:38–45:03](https://www.youtube.com/watch?v=__72lXKGtRs&t=2618s)); the later presentation promotes adaptive scores at night ([8BV, 1:02:24–1:03:22](https://www.youtube.com/watch?v=8BVb2DI3jic&t=3744s)). Different versions and conditions cannot be reduced to one session rule. The older meter's threshold and newer threshold are likewise not interchangeable.

Vendor success anecdotes, historical pricing/trials, promised correlation matrices, relative-strength displays and APIs are promotional or forward-looking statements. They are not verified performance, current product specifications or recommendations. No brokerage, vendor subscription or trading account was opened. No performance claim or correlation rule was backtested.

For a later empirical study, Abacus would first have to define the session/contracts, data source and latency, normalization window, observation baseline, related instruments and expected sign, measurable agreement/disagreement, entry and invalidation, management and costs. It would also have to preserve failures and news-driven breakdowns. Those are research requirements inferred here, rather than recovered mechanical rules taught by Vern.

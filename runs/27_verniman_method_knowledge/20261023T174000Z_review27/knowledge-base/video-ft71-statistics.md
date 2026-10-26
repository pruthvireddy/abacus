# FT71 — statistical research as preparation for execution

Primary media: [YouTube video iAt4YtiY-WA](https://www.youtube.com/watch?v=iAt4YtiY-WA), embedded in Vern's [Trade Management](https://verniman.blogspot.com/2014/04/opening-update-0408.html) page. The host introduces FuturesTrader71 and a webinar on statistical analysis. This note abstracts **FT71's teaching selected by Vern**; it does not establish that Vern implemented every example.

**Review coverage:** complete English auto-generated transcript read, from **00:00 through 1:20:25**, all **1,632 lines**, including presentation, Q&A and closing quiz. No audio verification or video chart-frame inspection was performed for this note. ASR contains malformed numbers and names, and a discontinuity from 34:59 to 35:28. The source workbook/data were not recovered or rerun.

Retained transcript identity: `transcripts/iAt4YtiY-WA.txt`, 68,489 bytes, SHA-256 `06628f37aa1348211968bfaa98f806e4b0d563a886978d3309e5a5a80764159b`. This is the staged capture identity, not a claim that YouTube's captions are permanent.

## The process FT71 teaches

At [02:16–03:42](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=136s), research is preparation for an actual execution decision. Tools, psychological readiness and market knowledge converge when the order is placed. Finding an interesting fact is therefore an intermediate result.

At [08:11–11:53](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=491s), he separates three attributes: discipline, thinking probabilistically and accepting that the next outcome remains unknown. He also questions research precision that costs substantial effort without changing a decision. His examples of improved percentages illustrate that tradeoff, rather than reporting a measured benefit from more computation.

His empirical sequence is concrete:

1. **Match the study to the trading horizon** ([12:00–13:53](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=720s)). A multiday tendency may offer little help to someone who only holds for minutes.
2. **Write the question before exploring the data** ([13:55–15:21](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=835s)). Otherwise unrelated discoveries can displace the purpose of the study.
3. **Construct comparable observations and check alignment** ([18:08–23:58](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1088s)). In his example, overnight and day-session records must refer to the same trading date; he spot-checks formulas against displayed observations.
4. **Count distinct events separately** ([23:58–30:46](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1438s)): upper boundary, lower boundary, both and either. An AND event is different from an OR event.
5. **Inspect distributions and exceptions** ([31:36–41:27](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1896s)). He filters failure cases, examines their ranges and acknowledges holiday contamination and a small failure subset.
6. **Return to entry, risk and context** ([30:50–31:28](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1850s), [56:42–1:04:28](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3402s)). A frequent event still needs a viable way to participate.

## His demonstration and what its measurements mean

The question at [18:08](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1088s) asks how often ES's day session reaches or exceeds the preceding overnight high or low. His historical chart settings describe overnight data around 15:30–08:29 Central and a day session around 08:30–15:15 Central. These are the demonstration's session definitions, not a current ES-hours specification.

The formulas at [23:11–25:32](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1391s) use greater-than-or-equal and less-than-or-equal comparisons. Consequently a **touch qualifies**, even when the speaker informally calls it a break. The transcript reports 1,974 session pairs, approximately 63% upper touches, 60% lower touches, 28% both and 96% either. These are historical spoken demonstration results, with rounded rates. They are neither reproduced Abacus results nor present-market probabilities.

At [30:50–31:28](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1850s), he explicitly rejects turning the 96% event directly into a system: frequent small wins can coexist with sufficiently large losses. At [1:02:30–1:04:28](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3750s), a level breaking by one tick illustrates why an event definition is not a profit-taking model. Costs, entry, distance traveled, stop distance and holding horizon remain separate questions.

At [51:21–56:24](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3081s), he treats estimates as properties of a finite historical sample and warns against optimizing that sample. At [1:04:48–1:06:09](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3888s), the host and FT71 emphasize expectancy and the damage from infrequent large losses. This is stronger than selecting the highest win percentage.

## Context can constrain an otherwise attractive statistic

At [56:42–59:38](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3402s), FT71 gives a reversal-day, gap-up example: the developing auction can make him size a statistical short idea smaller. He describes statistics as support for understanding which side is achieving its purpose, rather than as a replacement for reading the session.

At [1:00:47–1:04:28](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=3647s), he discusses evidence that discourages a trade without necessarily authorizing the opposite trade. His repeated-top example lacks a defined long entry and risk even when he would avoid shorting. He calls its recalled percentages old and tells listeners to do their own work. No repeated-top threshold becomes a rule here.

## Abacus analytical audit

These qualifications distinguish a useful research lesson from a validated trading specification:

- **Event incidence versus conditional probability:** at [42:20–44:25](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=2540s), the presentation uses the 28% whole-day both-boundaries frequency to discuss the chance of reaching the opposite side after one boundary breaks. Taking its complement does not itself establish that conditional chance. A test needs an explicit first-break/time definition, a denominator of eligible first-break cases and the subsequent path.
- **Distribution versus normality:** the histogram discussion usefully resists reducing a distribution to one average. However, the repeated identification of 68% with one standard deviation depends on a normal distribution; it is not a general property of a skewed distribution. The historical range figures and manually selected coverage are not portable volatility bands.
- **Sample sufficiency:** his statement around [25:52](https://www.youtube.com/watch?v=iAt4YtiY-WA&t=1552s) that more than 250 observations can suffice is his practical opinion, not a universal statistical guarantee. The appropriate sample depends on the event, precision, dependence and regime coverage.
- **Limits of the available evidence:** day-session high/low bars establish whether a boundary was reached by the end of a session, not entry timing or which boundary was visited first. Holiday choices, source quality, contract construction, filter changes and workbook formulas remain unreproduced. Choosing exclusions after seeing failures requires a separate declared study decision.

## How to use this lesson in Abacus

This is a proposed research workflow, not research already executed: state one causal question; freeze instrument, sessions and timestamp alignment; define touches/breaks and denominators; preserve missing cases; inspect the distribution and adverse cases; specify entry/risk/costs independently; and assess new data separately from discovery. A statistic that prevents a poor trade can be useful without becoming an entry signal. None of this licenses importing the video's historical percentages into a current strategy.

# Reading path, practice and decision records

These are **Abacus learning aids** built from the reviewed sources. They are
not Vern's supplied forms, a strategy implementation or instructions to take
live trades. The purpose is to make the teaching discussable and reviewable.

## A reading order that preserves dependencies

1. **Vocabulary and auction:** read the [glossary](glossary.md),
   [Auction Theory](topics/t03-auction-theory.md),
   [Markets in Profile](topics/t17-markets-in-profile.md) and
   [connected model](method-model.md). Explain balance, exploration and new
   acceptance in your own words before discussing entries.
2. **Location and destination:** read [Trading Value](topics/t18-trading-value.md),
   [Value Transition](topics/t16-value-transition.md),
   [level roles](levels.md) and [chart cases](chart-cases.md).
   Identify what makes an entry reference different from a destination.
3. **Observe the response:** read the [Bookmap course](bookmap-course.md),
   [execution examples](video-execution.md),
   [order-flow review](video-order-flow-review.md) and
   [audio/correlations](video-audio-and-correlations.md).
   Distinguish displayed liquidity, executed activity and resulting progress.
4. **Risk and expectations:** read [Vern's plan](topics/t01-the-trading-plan.md),
   [FT71 management](video-ft71-risk-management.md),
   [statistics audit](topics/t06-about-statistics.md) and
   [FT71 research process](video-ft71-statistics.md).
5. **Behavior and practice:** read [Douglas and motivation](video-psychology.md),
   [practice videos](video-practice-and-heatmap.md),
   [scalping comparisons](video-scalping.md) and
   [the tensions register](unknowns-and-tensions.md).

## A pre-session scenario sheet

Record the actual contract and clock/session conventions first. Note the
larger auction range, previous-session value and extremes, overnight structure,
scheduled catalysts and which references are already available. This follows
the order in Vern's trading plan; it does not specify a new level algorithm.

Write alternatives rather than one forecast. For each, name:

- The context in which it applies.
- The location to investigate and the reason it matters.
- The candidate destination and intervening structure.
- The observation that would support or refute the scenario.
- What remains unknown, including whether risk could be accommodated at all.

Include a standing-aside scenario. Dalton's article encourages three possible
scenarios; the point is contingency preparation, not forcing three trades.

## A candidate-decision record

```text
Timestamp and available evidence:
Current auction hypothesis:
Reference level/session and first-available time:
Observation expected here:
Actual transaction activity:
Actual displayed-liquidity behavior:
Actual price response:
Intermarket observation, if relevant:
Destination / structural invalidation / intervening obstacles:
Decision: investigate further / pass / simulated action under a separate drill
Reason, recorded before looking at the later outcome:
```

This structure discourages treating a large print, delta divergence or a bright
heatmap strip as self-sufficient evidence. It also makes a correct decision to
pass visible even when a later screenshot makes the move look obvious.

## Four useful learning exercises

| Exercise | Original task | Completion evidence |
|---|---|---|
| Explain a level | Select one of the reviewed chart cases; label location, destination and invalidation separately | Written explanation with source reference and uncertainty |
| Price versus value | At successive replay checkpoints, describe whether activity is returning to the old center or building elsewhere | Time-stamped notes based only on information then visible |
| Flow versus response | Compare executed aggression with progress at a named location; list an alternative explanation | Short observation record; no inferred participant identity as fact |
| Review process errors | In a simulator drill, review early/late entries, repeated wrong-side attempts and arbitrary changes separately from P&L | An execution log, realistic simulator settings and one specific process correction |

The source drills can inspire these tasks, but exercise completion does not
establish an edge. A randomized-direction drill studies fill/management skills;
it is not evidence that random entries are profitable. A historical chart
classification can also benefit from hindsight, which must be disclosed.

## End-of-session review

Compare the written alternatives with the observations actually available at
each decision. Separate invalid hypothesis, poor location, missed evidence,
execution deviation and ordinary unfavorable outcome. Keep good process/loss
and poor process/win cases. Review missed trades without rewriting a late
entry as the original opportunity.

Choose one concrete change to observe in the next **practice** session. Record
any altered rule before the next sample; do not repeatedly optimize against
the same examples and call that validation. This repository contains a source
study, not completed drill sessions or verified training results.

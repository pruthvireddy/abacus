# Decision and experiment history

## 2026-09-24 — scope and pre-outcome design

The repository currently ends at study 10, so this work uses the unused ID
`11_vwap_conditional_probabilities`. Prior study 05 and 06 protocols, input
locks, reports, event definitions, and strategy cards were reviewed. The DR/IDR
repository was inspected read-only for its presentation discipline: few active
levels, exact deadlines, separate reached/expired/unavailable states, hoverable
support and denominator details, frozen historical probabilities, and no silent
conversion of target frequencies into trade claims.

The design reuses the published one-tick causal contact zone and completed-bar
availability conventions. A/B survival is explicitly defined against the
causally known evolving VWAP, while forecast outcomes keep checkpoint-frozen and
causal-evolving references separate. Fresh departures require an observed armed
state; already-away warm-up states do not receive a fabricated departure time.
Repeated ten-minute checkpoints remain linked to one episode.

C uses a fixed 30-minute signal lockout, not outcome-dependent rearming, so the
feature-only gate can assess support without reading future paths. The minimum
corridor width is the only threshold to be selected at the gate. Candidate tick
floors are 4/8/12/16 and day-sigma floors are 0/0.10/0.25/0.50. Selection will
prefer the smallest mechanically meaningful joint rule that preserves useful
product/session support; outcome rates cannot influence it.

No future outcomes have been calculated at this point.

## 2026-09-24 — abandoned feature-only gate and correction

Feature-only run `20260924T154346Z_vwap11` verified all pinned identities and
created no outcomes. It revealed that the first implementation allowed the
30-minute residence/slope lookback to overlap the anchor's 30-minute warm-up,
although the written plan reserved that context until anchor age 60 minutes.
The stricter written definition was retained. Earlier checkpoints/events remain
eligible for geometry-only estimates, but their added path context is explicitly
unavailable. A fresh feature-only run is required before protocol freeze.

## 2026-09-24 — corrected feature gate and protocol freeze

Corrected feature-only run `20260924T155331Z_vwap11` reverified all pinned
manifests and partitions. It retained 489,856 primary two-minute checkpoints
from 55,635 fresh episodes across all 3,039 eligible product-sessions, plus
271,620 five-minute Globex checkpoints. The 26,549 base two-minute corridor
crosses had no future outcome attached.

The feature-only corridor distribution supported the joint minimum of eight
ticks and 0.25 current day sigma. After the fixed 30-minute lockout it retains
15,078 two-minute events across 2,962 product-sessions: 4,347 Asia, 6,088
London, and 4,643 NY. The smallest product/session cell has 953 events. Four
ticks was rejected mechanically because two ±1-tick target zones would leave
only two ticks of interior space; larger floors discarded support without a
feature-only reason.

Development-only prior ATR14 terciles are ES 67.3036/84.0 points, NQ
261.5060/333.1548, and GC 26.4881/36.5405. The fixed distance, elapsed,
excursion, corridor-position/width, and geometry bins in protocol 1.0.0 are
rounded feature-distribution landmarks, not outcome-selected thresholds.
Path context is available for 98.0% of development A/B checkpoints and slope
context for 80.9% of base corridor candidates under the stricter 60-minute
anchor-age rule. Protocol 1.0.0 was frozen before opening future paths.

## 2026-09-24 — execution, verification, and interpretation

Run `20260924T155331Z_vwap11` opened future one-minute paths only after protocol
freeze. It retained 489,835 outcome-capable primary checkpoints from 55,623
episodes; 21 additional checkpoints were null because tick rounding placed the
checkpoint close inside the return zone. All 15,078 selected primary corridor
events had complete future evidence. The five-minute sensitivity produced
271,597 outcome-capable checkpoints and 12,894 corridor events from the same
underlying dates and is not an independent sample.

Product-specific primary rates were:

- frozen VWAP contact within 30 minutes: ES 22.0%, NQ 20.5%, GC 19.8%;
- frozen VWAP first versus a 0.5-sigma extension: ES 17.1%, NQ 15.9%, GC 15.4%;
- frozen day VWAP first after session-VWAP corridor failure: ES 21.2%, NQ
  20.9%, GC 14.1%.

The complete competing-class vectors matter more than the selected component.
Extension was first in 42.4%–45.9% of A/B checkpoints and neither resolved in
37.0%–42.1%. Session VWAP was reclaimed first in 74.3%–80.3% of corridor events;
neither and same-minute ambiguity were retained. Frozen and evolving VWAP
contacts also differed: evolving-only 30-minute contact contributed about
1.8%–2.0% of checkpoints.

On the combined 2024–2026 chronological evaluation, the prespecified added A
context reduced Brier error by 0.0007 (0.5% relative) and B context by 0.0028
(1.0% relative), but supported specific cells covered only 10.7% and 14.6% of
rows. No C added-context cell cleared the frozen 100-observation development
floor, so it fell back entirely to geometry/clock estimates. These are small or
unsupported increments, not grounds for a richer default chart panel.

Verification rehashed 108 pinned inputs, reconciled 761,476 A/B and 27,972
corridor evidence rows across both timeframes, preserved null-versus-false and
all exhaustive outcome classes, independently recounted 33 examples from the
one-minute source, checked all report links and SVG labels, and passed 12 focused
edge-case tests. The mechanically selected figures were visually inspected.
No protocol threshold changed after outcomes were opened.

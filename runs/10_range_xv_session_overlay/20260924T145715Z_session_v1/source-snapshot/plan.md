# Asia, London, and New York overlays on studies 07–09

Recorded 2026-09-24 after all three source studies were inspected. This is an
**exploratory, retrospective** cross-study overlay. It reuses saved event and
outcome ledgers; it does not amend their sealed results or create a new trading
rule. The source studies have different samples, horizons, and clocks, so their
rates and returns must not be pooled or ranked against each other.

## Sources and clock

Pin the selected sealed runs: 07 `20260924T004900Z_rxv07`, 08
`20260924T132916Z_ctbars_v1`, and 09 `20260924T141810Z_c2confirm_v1`.
Study 07 spans 2024-08-14–2026-09-07 and retained pre-normalization event
outcomes. Join its saved zero-based `signal_index` to `source_row = index + 1`
in each now-normalized short-history enhanced CSV, after excluding the original
partial 2026-09-08 session. Verify the migration crosswalk, event/source row
identity, source timestamp clock, unchanged session date, and strict signal
completion. Use the corrected completion wall time only to label the **saved**
07 events. The quiet-breakout event selection and calibration used the older
export-clock half-hours; a session overlay of those cohorts is descriptive,
not a corrected rerun of that idea. Studies 08 and 09 already use corrected
long-history inferred New York wall time. ATAS timezone is unverified.

Segments are half-open decision-time New York wall-clock windows: Asia
18:00–03:00, London/pre-NY 03:00–09:30, New York 09:30–16:00. Preserve
16:00–18:00 as `transition` coverage, outside the three segment contrasts.
Study 07 and 08 use the signal bar's strict completion proxy. Study 09's
confirmed C2 and ordinary B2 comparisons use C2/B2 completion; common-C1
opportunity and price tables use C1 completion. The wait policy in 07 is
grouped by its original C1 decision to keep its early-policy comparator on
the same opportunity set. No outcome crosses a source study session boundary.

## Saved-study outcomes and comparisons

**07:** Keep ES 6RXV, NQ 20RXV, and GC 20RXV separate. For each product,
idea, and segment, summarize the same saved primary candidate and control:
pullback `extreme_break` vs `unfiltered`, exhaustion `wait_policy` vs
`early_policy`, quiet breakout `quiet` vs `not_quiet`. Net ticks per original
opportunity equal saved signed `return_ticks` minus two ticks per `traded`
event; no-trade wait opportunities remain in the denominator at zero. Report
candidate net mean, candidate-minus-control mean, gross mean, trades,
opportunities, dates, and session-cluster intervals. Also show development,
validation, and final blocks. The 27 comparisons form one exploratory
Bonferroni family. A provisional segment standout requires support, adjusted
lower bounds above zero for both candidate net and candidate-minus-control,
and positive differences in all three blocks. This is stricter than a point
estimate and still not a profitability claim.

**08:** On main C1 events with prior run ≥3, primary horizon eligibility,
and the source study's GC exclusions, report `P(C2 and C3 follow C1)` by
chart, C1 direction, and segment. Contrast each segment with the **other two
named segments** of the same chart and direction, using joint session scores.
Report three chronological blocks and original prior-length bins as
descriptive subtables. The 42 chart/direction/segment comparisons form one
exploratory Bonferroni family. A standout requires support, adjusted lower
contrast above zero, and positive contrasts in all three blocks.

**09:** On confirmed main C1/C2 pairs, report `P(C3 and C4 follow C1)` by
chart, direction, and C2 decision segment against both the same-segment
ordinary B1/B2 two-future-bar baseline and candidate decisions in the other
two named segments. Retain three chronological blocks. Each of these two
42-comparison families is exploratory and separately corrected. A
chart-state standout versus ordinary needs support, an adjusted positive
ordinary contrast, and positive contrasts in all three periods. A segment-
specific standout additionally needs a positive adjusted segment-vs-other
contrast and all-period agreement. Separately report C2 confirmation,
immediate C2+C3 success, wait C3+C4 success per original C1, and the signed
two-bar price proxies grouped by **C1** decision segment. Zero wait-policy
movement for nonconfirming C1s stays in the denominator. Never interpret a
bar-count standout as a price or execution edge.

For rates, save numerator, denominator, dates, events/date, rate, and 95%
session-cluster sandwich intervals. For contrasts and means, use joint
session-cluster scores with normal intervals; Bonferroni lower/upper bounds
use 0.05 divided by the declared family size. Minimum support is 300
candidate events, 100 dates, and 2 events/date; each chronological block
needs at least 30 dates for the stability screen. Report negative and
unsupported cells too. Settings within ES/NQ/GC share trades and are not
independent replications. The 07 short-history period overlaps the long
history of 08/09; cross-study agreement is contextual, not validation.

Verify source artifact hashes, disjoint 08/09 segment count sums, 07 mapping
and saved whole-cohort return arithmetic, 09 candidate/ordinary disjointness,
and spot traces. Derive report claims from saved numerical tables. Stage the
new evidence under `work/`, then seal a unique local run with code, input,
environment, exclusion, command, check, and artifact identities.

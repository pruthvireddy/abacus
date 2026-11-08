# Verniman Levels

Study `29_verniman_level_reconstruction` · Phase 1 indicator implementation

**Verniman Levels** builds a session-qualified candidate map from the user's
supplied Pine baseline and provides a completed-bar pre-open snapshot, default
09:25 New York. It keeps developing RTH levels separate. It does not recover
Vern's HVE/PBT/LIS algorithms or select a pivot, targets or trades.

Start with the [Pine script](indicator/verniman_levels.pine),
[calculation specification](specification.md), [Phase 1 plan](plan.md),
[changes](changes.md) and [verification results](verification.md). The
[original](reference/vp_levels_original.pine) remains unchanged; its
[manifest](reference/source-manifest.json) records SHA-256
`aaa95a7e639b027637c6eb6ab0c9e5c8fa096f16b069f5e1a9a418f65c08094b`.
The [settings](study.yaml), [input lock](inputs.lock.json) and
[decision notes](notes.md) record scope and provenance.

## Phase 3 experimental candidate map

The separately authorized [Phase 3 implementation](phase3/README.md) adds the
unfitted N1/E1 node/edge control, fixed three-RTH composite and manual P1/P2
arithmetic. Its [verification](phase3/verification.md),
[ten-date training status](phase3/training-results.md) and
[Phase 4 handoff](phase3/phase4-handoff.md) record the native/data blockers.
Phase 3 is not ready for empirical selection research; new training targets
remain closed until all seven first-pass expanded maps are retained. The Phase 1
and Phase 2 text below remains its original phase record.

## Phase 2 training examples

The separate [Phase 2 review](phase2/README.md) studies October 1, 2 and 5, 2026,
under its [frozen protocol](phase2/protocol.md) and
[input declaration](phase2/input-declaration.json). Target access is authorized
only for those three dates after retaining neutral baseline maps. All other
target dates remain protected. This phase produces source-backed cases and an
extension specification; Pine calculations and automated selection stay unchanged.
The Phase 1 settings and verification below remain their original phase records.

## Install privately

1. In the logged-in TradingView account, make a separate study layout or copy
   the existing layout so the current setup is preserved.
2. Open Pine Editor, create a new indicator, and paste the complete contents of
   [verniman_levels.pine](indicator/verniman_levels.pine).
3. Save it privately as **Verniman Levels** and add it to the study chart.
   Do not publicly publish it. Record any compiler/runtime message.
4. Inspect the actual symbol/contract and feed, session, adjustment settings,
   chart type, timeframe and history. Retain these with the verification record.

Source-text or Python checks do not establish that TradingView accepts the Pine
script. Consult [verification.md](verification.md) for the actual compilation
and browser replay status; installation instructions are not evidence of success.

## Supported settings and readiness

Use a **standard 1-minute or 5-minute ES, MES, NQ or MNQ futures chart with full
electronic-session bars**. Sessions use `America/New_York`: futures 18:00–17:00,
RTH 09:30–16:00 and overnight 18:00–09:30. Sunday evening belongs to Monday's
trading date; the futures week begins Sunday 18:00. Record whether prices are
an individual unadjusted contract or a continuous adjusted series.

Load at least a complete preceding futures week and all bars from the current
week's start for the full weekly map. A partial initial week, missing required
bars, zero-volume profile, missing cutoff boundary or unsupported chart produces
an unavailable/status result for affected references. RTH-only charts cannot
supply overnight/full-session/weekly families. Holidays/early closes are not a
recovered exchange calendar; a shortened period fails the full-period gate.

The 16-tick rows and 70% value area are inherited defaults. Each profile is
bounded to 6,000 bins; overflow withholds it and requests a larger row size.
Missing or negative volume invalidates the profile; individual zero-volume bars
are permitted when period total volume remains positive. Price extrema and
the last-traded close use their own bar-coverage gate. The profile spreads
each chart bar's volume uniformly over touched bins, so levels depend on
timeframe and row size. They are approximate candidates, not exact observed
volume at price or proven Verniman settings. Use the family toggles to reduce
clutter and the compact status table to inspect period identities/readiness.
Enable **Expand table with all candidate values** to show the 19 frozen and
19 live candidate fields side by side; this expansion defaults off. The separate
optional live lines default off; the three developing RTH references default on.

Full-session extremes, completed-RTH extremes and ONH/ONL have separate labels.
YVAH/YPOC/YVAL refer to the latest completed 09:30–16:00 RTH in the pre-open
map. Live labels say **Completed RTH** and qualify the Y aliases as pre-open;
after today's RTH completes, the latest completed profile is today's.
The prior close is the last retained completed-RTH bar close, **not official
settlement**. No actual RTH opening gap is added to a pre-open map.

Previous-week references roll at the next Sunday 18:00 New York week boundary;
Friday 17:00 completes the current week without relabeling it as previous week.
At a new trading date, full-session and RTH references must come from the expected
prior weekday, or Friday for Monday. An entirely missing day therefore clears
older references. The fixed-clock rules do not infer a holiday substitution.

## Replay a frozen pre-open map

Only **October 1, October 2 and October 5, 2026** are permitted Phase 1 browser
verification dates. Do not open dated Vern target charts, private observations,
daily-level answer rows or hidden-test dates.

1. Use identical chart/settings/history across comparisons. Load a full prior
   week plus the current week's history and inspect readiness.
2. Set the New York cutoff, default 09:25, to an aligned completed-bar boundary
   before 09:30. On 5-minute bars the default includes 09:20–09:25; on 1-minute
   bars it includes 09:24–09:25. An unfinished/straddling bar is excluded.
3. Replay to the cutoff. Enable **Expand table with all candidate values** and
   save snapshot time, last included bar, candidate values,
   source periods, readiness and actual chart/feed/session/adjustment settings.
4. Advance into RTH. Confirm the saved map and its source identities remain
   unchanged while developing references can change.
5. Restart or reload at the same cutoff and compare every available saved value
   and identity. Record unavailable references and reproduction differences.

The freeze resets for a new futures trading date. A reload recomputes it from
retained history; it cannot preserve values across changed settings or corrected
feed data. Drawing a line at an earlier coordinate never makes a later value
available earlier. See [the boundary specification](specification.md#snapshot-boundary-and-presentation).

## Local verification

From the workspace root:

```sh
./scripts/check-workspace --context study-29
./scripts/check-workspace --check study-29
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 scripts/build-research-index.py --check
```

Study execution uses the existing locked environment without sync. Synthetic
session/arithmetic checks are independent specification checks;
they do not execute Pine or reproduce actual TradingView replay. Additional
registry/tooling/default checks required by changed files and all actual outcomes
belong in [verification.md](verification.md). Stage fresh evidence under
`work/29_verniman_level_reconstruction/<verification-id>/`; no incomplete run is
sealed and no historical research is rerun.

After this baseline is verified, the next authorized research phase can study
training-day examples to define HVN/HVE candidates and PBT constructions. All
later segmentation, composite, LIS/pivot and ordered-target work remains planned
and unexecuted under [the protocol](plan.md#later-modules--planned-not-implemented).

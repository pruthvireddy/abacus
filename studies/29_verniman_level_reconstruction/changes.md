# Changes from the supplied baseline

Study `29_verniman_level_reconstruction` · Phase 1 · 2026-10-30

The [original Pine source](reference/vp_levels_original.pine) is preserved byte
for byte, including CRLF line endings. Its SHA-256 is
`aaa95a7e639b027637c6eb6ab0c9e5c8fa096f16b069f5e1a9a418f65c08094b`.
[The source manifest](reference/source-manifest.json) records its locator and
size. The separate [derivative](indicator/verniman_levels.pine) is titled
**Verniman Levels**.

| Area | Baseline behavior | Intentional correction |
|---|---|---|
| Session rollover | In-session/out-of-session transitions | Explicit NY period identities/timestamps survive omitted break bars and separate RTH-only days; out-of-full-session bars do not mutate state |
| Initial history | Partial initial profiles appear usable | Coverage and exact-boundary readiness; incomplete families unavailable |
| Profile reset | Clears bins/total but retains old levels | Reset clears VAH/POC/VAL; empty/zero/invalid profile cannot display stale values |
| Previous RTH | Duplicated RTH accumulators and display switch | Latest completed RTH stored distinctly from developing current RTH; Y aliases qualified as pre-open |
| Missing whole sessions | Older levels can survive unnoticed | Require the expected prior weekday (Friday for Monday) for completed full/RTH references; adjacent prior week for weekly references |
| Weekly boundary | Exchange/chart `time("W")` rollover | Declared Sunday-18:00 NY futures-week identity and strict warm-up; previous week rolls at that boundary, not Friday's completion |
| Overnight completion | Retains earlier values even without a terminal bar | Require the last included overnight bar to end at the exact requested through-time or 09:30 completion |
| Price references | Full-session PDH/PDL with ambiguous short labels | Full-session extremes explicitly named; separate completed-RTH and overnight extremes |
| Closing reference | None | Prior completed RTH's last retained close; no settlement claim |
| Information timing | Calculations can update with developing bars; backward anchor | Confirmed-bar updates; copied pre-open map with last included bar and availability timestamp |
| Replay snapshot | None | Once-per-trading-date freeze at configurable pre-RTH cutoff, default 09:25 NY |
| Unsupported coverage | Plausible values without a status | Per-family readiness/status and bounded profile resources |
| Missing terminal bar | Developing RTH may remain as a stale prefix | Require RTH coverage through the expected completed boundary; status shows effective ON/RTH coverage, live processing time and completed-RTH source date |
| Status presentation | No readiness table | Compact status by default; optional expanded frozen/live candidate values |
| Terminology | VP Levels, PDH/PDL and period abbreviations | Verniman Levels; readable session-qualified profile/extreme labels |

The uniform touched-bin allocation, lowest-bin POC tie, upward-first adjacent VA
tie and bin-base price coordinates remain the baseline arithmetic. Default
row size and VA percentage remain provisional. No additional HVN/HVE/LVN/PBT,
LIS, target selection or opening-gap formula is added. The
[specification](specification.md) records the approximation, supported settings
and unavailable states. [Verification](verification.md) distinguishes these
intended changes from actual local and TradingView evidence.

# Planning decisions

## 2026 September 29

The user requested a fresh plan and a copyable implementation prompt for three
anchored-VWAP questions: post-band-close MAE/MFE and close behavior, probability
of returning to VWAP, and post-return bounce/fade behavior. The requested output
separates Asia, London, New York and optionally the full Globex day; the plan
includes all four. The current turn is planning only. No new research code,
outcome computation or indicator work is authorized for this planning turn.

Study 15 was unused when this directory was created. The handoff prompt gives
the receiving coding agent explicit implementation/execution instructions.
Existing study 05/06/11 evidence is preserved, not deleted or relabeled.

Working assumptions pending any user clarification: delta means price change;
both bounce toward the original excursion side and continuation through VWAP
are measured. The user mentioned 15 candles before repeating 5/10/20/50, so
15 is retained as a supplementary horizon. ES/NQ/GC inherit the requested
existing-study context, with products kept separate.

Proposed methodological choices are explicit in [the plan](plan.md): first
crossing per threshold per VWAP-separated parent, next-open measurements,
session-contained complete horizons, evolving VWAP primary and frozen VWAP
secondary, both directional responses, and a symmetric 0.5-touch-sigma race.
Early valid signals are included; the old 30-minute warm-up is only a declared
sensitivity. These are proposed defaults, not numerical findings.

Read-only catalog inspection verified that the feature release uses completed
output-bar HLC3 and population sigma, its local session windows end before the
anchor calculations do, and OHLCV has no true aggressor-volume delta. Existing
input manifest pins are retained in the new study lock; full partition
verification is assigned to the implementation agent before outcomes.

No protocol is marked frozen, no reference run is selected, and there are no
new computed outcomes. Planning verification consists of documentation/link
checks, metadata/input-pin consistency and a regenerated research index.

## 2026 September 29 Chart companion request

The user subsequently supplied a GC MAE/MFE Pine indicator and explicitly asked
for its display style and cooldown statistics on top of the VWAP OE indicator,
for the one rule of fading a two-minute close outside an anchored VWAP's two-sigma
band. This authorizes the [chart companion](pine/README.md), independently of
executing the three-module historical study. The old planning scope above is a
record of the earlier request, not a prohibition on this later authorized work.

The new companion measures longs below the lower band and shorts above the
upper band from the next contiguous open. It defaults to every outside close,
with optional fresh crossings, and maintains five independent cooldown cohorts.
This follows the pasted chart-study convention rather than claiming to implement
the broader plan's parent-excursion logic. The original OE's Asia 20:00–00:00
and London 03:00–08:00 inputs are retained; users may choose wider windows.
Both original sources are preserved in `pine/`; new script/provenance and
numerical helper tests live with this study. No saved run or result table was
modified. No external script was uploaded or published.

Local helper tests passed; Pine Editor compilation and visual replay are not
verified. The study remains planned and has no selected reference run.

## 2026 September 29 Chart rendering correction

The user supplied a TradingView screenshot reporting RE10140 (74 plot counts,
limit 64) and accepted drawing only the last two days of VWAPs while retaining
historical buy/sell markers. The editable companion now draws the latest two
observed daily occurrences of each anchor using bounded polylines, removes the
invisible gradient fills, and leaves markers and statistics across loaded
history. Weekend gaps do not count as observed sessions. The statistical engine
is unchanged. Local helper and rendering-queue checks passed; native acceptance
of this revision still needs TradingView verification. Existing sources and
sealed evidence remain unchanged.

## 2026 September 29 Historical execution and explicit reference selection

The current user request authorized implementation, local execution, reports and
sealing of the full three-module historical study. Its frozen executable is
[protocol 1.0.0](protocol-1.0.0.md), with machine settings and exact source hashes
in [the freeze record](freeze.json). The completed feature-only pilot covered
2,096,910 bars before freeze at 2026-09-29 23:39:12 UTC. Outcomes began afterward.
The pilot clarified that a session-opening `contains_roll` flag does not itself
indicate a within-path contract break; exact raw identities and adjustments
control continuity. No outcome-driven definitions or sample changes were made.

The run [20260929T234000Z_a15f](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/report.html) is selected explicitly
as the reference after all numerical audits, source recounts, uncertainty checks
and offline report inspection passed. Selection is for verified completeness,
not performance or recency. The [advice](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/advice.md) preserves inconclusive
and opposing evidence. No older statistical estimate was reused. No strategy
card, old study/run, package or released dataset was changed.

The run has 42,096 parents, 67,392 threshold signals, 35,843 touch events, and
516,175 horizon records; it includes five HTML/Markdown reports, 9,260 summary
cells and 144 SVG figures. [Verification](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/verification.json) records
3,240 main-cell reconciliations, 1,888 independent raw-source horizon recounts,
20 research synthetic tests, and preservation of 1,740 prior files. A separate
check independently reproduces 120 bootstrap intervals. The broad discovery
log contains 35 passing tests because it also discovers 15 tests for the
separately developed chart companion; the research's own pre-outcome suite is
the 20 tests in `test_engine.py` and `test_inputs_stats.py`.

The companion `pine/` files and its test appeared through concurrent separate
work while this execution was underway. They were preserved, not implemented or
edited by this research task. Directory source snapshots incidentally retain
those files/test; the research entry points do not import or consume them.
The test-count field 20 refers to the historical study's tests, not the total
broad-discovery log. The companion's separate documentation above is retained.

The browser rejected local `file://` HTML inspection. No browser/serving bypass
was attempted. Static SVGs were rasterized locally and visually inspected;
HTML tables, local links, source values and offline structure passed automated
checks. Browser layout remains explicitly unverified. Numerical results are not
affected by this presentation limitation.

Large ledgers are copied into configured permanent Sahadeva research storage
with row counts, hashes and locators in [events.manifest.json](../../runs/15_vwap_excursion_response/20260929T234000Z_a15f/events.manifest.json).
They are outside ordinary Git history and no longer depend on scratch retention.
The retained local copy is verified; off-device backup is unverified. Source
coverage remains retrospectively selected and ends 2026-09-18; true volume delta
is unavailable. Price-path behavior does not establish executable profitability.

Navigation and final sealed hashes are recorded separately in
[completion verification](completion-verification.json), preserving the sealed
run unchanged. No external publication, deployment or orders were performed.

## 2026 September 29 Chart signal controls

The user requested a session-start moratorium and an adjustable fade sigma
threshold. The editable Pine companion now exposes both under VWAP Fade / Event
study: moratorium minutes default to 0 (30, 60 or custom permitted), and the
band multiple defaults to 2 (2.5, 3 or custom permitted). Moratorium expiry is
inclusive at signal close. VWAP accumulation and data validity are independent
of that pause, so a fresh crossing at expiry can use a valid paused prior bar.
Earlier crossings are not queued. These controls feed FADE candidates before
cooldown, with shared settings across markers, alerts, diagrams and tables.
Original OE triangles and local visual multipliers retain separate settings.

The focused chart-helper suite now has 23 passing tests. Native Pine compilation
and replay remain unverified. This change does not alter the frozen historical
protocol, its implementation or any sealed run, report, dataset or snapshot.

## 2026-10-06 — Phase 3 local publication navigation

Featured presentation: [20261006T230936Z_web15](../../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261006T230936Z_web15/publication.json) · [manifest](../../reports/exports/15_vwap_excursion_response/20260929T234000Z_a15f/20261006T230936Z_web15/manifest.json). Stable local study route: `/studies/vwap-excursion-response/`; immutable report route: `/reports/15-vwap-excursion-response-20261006-web/`.

Registered reference retained: `20260929T234000Z_a15f`. Catalog navigation is maintained in [Narada](../../apps/narada/content/studies.json). Saved findings, evidence status and research-reference metadata are unchanged. This is local static publication; no deployment or research execution.

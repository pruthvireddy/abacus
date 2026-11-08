# Phase 2: understand three training examples

Study 29 · source review completed 2026-10-30 · algorithms remain unimplemented.

Read the illustrated cases: **[October 1](cases/2026-10-01.md)**,
**[October 2](cases/2026-10-02.md)** and **[October 5](cases/2026-10-05.md)**.
Then use the [cross-case hypotheses](hypotheses.md) and
[Phase 3 specification](phase3-specification.md) to choose the next engineering
work. These are qualified structural explanations, not a recovered Verniman
formula, target-selection model or profitability finding.

## What the three cases support

Named overnight extremes sometimes agree closely with our neutral map. Source
value areas differ, especially October 2: source YVAH/YPOC/YVAL are
7744/7732/7696, versus our completed-RTH approximation 7724/7688/7680.
That mismatch can reflect profile data, session or construction choices; three
examples cannot isolate the cause. HVE labels appear at profile transitions and
in compound confluence labels. No explicit HVN/LVN segmentation rule or numerical
node/edge threshold was recovered.

The printed plans explain conditional divider/target roles, with directional
VIX/CVD conditions absent from our baseline. They do not identify a unique
selector. Weekly/composite maps carry references such as 7830 and 7856 across
cases. GAP and PBT can be compound labels; neither is automatically a current
overnight extreme, POC or value-area boundary. The October 5 PBT-ETH line gives
a useful projection example, but its causal center/bounds remain unidentified.

The source evidence contains no clearly specified prior last-traded closing
reference or official settlement for this comparison. GAP is not silently used
as a prior close. The X recap headers show after-16:00 bars, not official RTH
close or settlement. Our prior-RTH last closes remain 7712.75, 7726 and 7779 for
the three respective snapshots. Today's actual open/initial balance never enters
the 09:25 map.

Important conflicts remain: October 1 plan VPOC 6691 versus image 7691;
YVALH versus YVAL wording; earlier HVE-YVAH near 7779 versus plan HVE 7786;
October 2 daily GAP 7803 versus weekly HVE 7804; October 5 text/axis and
GAP/HVE differences. The inventory preserves each source occurrence.

## Evidence and reproducibility

The [protocol](protocol.md) and [input declaration](input-declaration.json) were
frozen before target review. All three fresh neutral 09:25 TradingView maps were
captured first and matched Phase 1's 19 fields. The current local Pine hash is
unchanged. Browser clipboard bytes differ only in CRLF versus LF, verified by
normalization without changing either saved source.

The [source manifest](source-manifest.json) pins release 13.0.0, exact filtered
source revisions, retained images, timestamps and qualifications. Six blog maps
and six dated X recap/technical images were visually reviewed from retained
bytes. No fresh X visit is claimed. Remote image filenames suggest pre-open
clocks, but their timezone is not printed and their captures are retrospective.
Historical pre-open availability remains unresolved; every original available_at
remains null. Closing posts support later presence only.

The [machine-readable inventory](level-inventory.json) contains **143 source
level occurrences**. Printed prices, aligned axis badges and coarse axis
intervals remain distinct. It includes named structural lines in the selected
maps/recaps and the plan's reference/conditional text. Execution arrows, P&L,
unnamed modal lines, floating indicator/current-bar readouts and IVR range widths
are not candidate price levels. [All-family comparisons](baseline-comparison.csv)
contain 2,717 descriptive distances, not a fitted selector or match-rate test.
Figures are original analytical illustrations; original third-party captures
remain private at their retained locators.

The optional fixed 8-tick comparison was not executed: the browser security
policy blocked creating an exploration layout. No alternative route or per-day
tuning replaced it. [Verification and access limits](verification.md) distinguish
this from the successful fresh baseline walkthrough.

## Local maintenance

The narrow selector [select_sources.py](select_sources.py) reads only through
the pinned public loader and exact intake filenames, then writes only allowed
dates to the private stage. The loader internally verifies/reads release tables
before filtering; unrestricted rows were never displayed to the model. Do not
replace it with an unbounded table dump or rerun historical publishers.

Recreate the inventory/comparisons from the already filtered stage:

```sh
python3 studies/29_verniman_level_reconstruction/phase2/build_review_artifacts.py
python3 studies/29_verniman_level_reconstruction/phase2/check_review.py
python3 scripts/check-agent-docs.py
```

[build_review_artifacts.py](build_review_artifacts.py) contains the explicit manual
image readings and produces no market-level detector. The presentation-only
[renderer](render_comparisons.py) uses bundled ReportLab/Sharp because matplotlib
is absent from the locked environment; no dependency or lockfile was changed.
Exact execution, byte preservation and check results are in
[verification.md](verification.md). No numerical research was rerun, no Pine
calculation changed, and nothing was published or deployed.

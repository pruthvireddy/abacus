# Phase 2 verification, access and limitations

Study 29 · 2026-10-30 · source review and design only. No Phase 3 implementation,
Pine changes, selector, profitability test, publication, deployment or sealed run.

## Ordering and baseline identity

The [protocol](protocol.md) and [input declaration](input-declaration.json) were
frozen at **22:25:42 UTC**, before target access. The stage's protocol-freeze.json
pins their bytes and the Phase 1 code/settings/verification identities.
Fresh TradingView neutral captures were saved at approximately 22:28:36,
22:28:59 and 22:29:16 UTC for October 1, 2 and 5. Their record was completed
before source selection began at **22:29:53 UTC**. All three tables showed 19/19
fields with the final included confirmed interval 09:20–09:25 New York and
matched the retained Phase 1 values. No day was substituted.

Current Pine SHA-256 remains
`5bbc40075cefb19feacb1a676c67ee5770cb5ef7023b9dd76781f2927a243f73`.
The browser showed the saved private Verniman Levels revision 3. Copying its
source through Pine Editor produced CRLF line endings; the local file uses LF.
After CRLF-to-LF normalization the entire source was identical, including its
final newline. This investigated difference is recorded in browser-baseline-identity
JSON files; neither source was rewritten.

Settings were checked in the live input dialog: standard CME_MINI:ESZ2026
5-minute candles, ETH, 16 ticks, 70% VA, 09:25 cutoff, expanded table, all
families enabled. The actual December contract has no continuous back adjustment.
The current chart remains the [Phase 1 layout](https://www.tradingview.com/chart/mtK3TbRP/).
This is a fresh baseline walkthrough, distinct from reusing Phase 1 screenshots
and its earlier compile/advance/restart verification. Phase 2 did not change or
recompile Pine and does not claim new native verification for other symbols.

## Source suitability and timing

The [source manifest](source-manifest.json) pins consolidated release **13.0.0**,
manifest SHA-256
`39a12cd01b131729908a6b7743a710eaefe73f86e7df9ecb66787787b88277bf`.
Exact one-day selections returned one canonical plan per date and 9/6/6 plan
level rows. There were no separate user-recollection rows for these dates.
The loader internally verifies/reads release tables before filtering. Only
allowlisted returned rows were serialized or displayed; no unrestricted table
entered model context. Three exact intake r001 records were inspected.

| Case | Filename clocks (timezone unprinted) | Claimed blog update, New York | Later technical-map post, New York |
|---|---|---|---|
| October 1 | 09:19:45 / 09:20:10 | 09:22:45.507 | 16:12:45 |
| October 2 | 09:12:01 / 09:12:23 | 11:30:48.874 | 16:05:22 |
| October 5 | 08:55:50 / 08:56:09 | 08:58:47.016 | 16:28:41 |

The blog images/post bodies were captured October 20; X screenshots were
captured October 28. Blog publication metadata reuses 2009 dates. Filename
clocks suggest earlier chart states if interpreted in New York, but do not
authenticate timezone or original publication. Even an early update claim
does not prove the retained content was available before cutoff. All original
available_at values stay null, and no level is classified as historically
certified pre-open. Closing timestamps support later presence only.

Six retained blog maps, three retained X technical maps and three dated /ES
3-minute recaps were inspected visually. Other agents independently checked
the October 2 and 5 readings and the technical-map set. These are **fresh local
pixel readings of retained captures**, not fresh X/browser source visits.
Delivery contract is explicit in plan text; chart contract identity is qualified
separately. Intraday MOC sources at 15:50–15:55 are later intraday commentary,
not after-close posts or technical-level revisions. The selected archive does
not establish exhaustive intraday or pre-open source coverage.

## Exposure and browser access

Only October 1, 2 and 5 target maps/text entered the review. Development and
hidden-test answers were not opened, and Replay did not navigate to them.
The allowed October 1 intake contained metadata for a weekly-context image
stated September 28. Its date/role/locator were seen; its pixels/targets were
excluded. No outside-date target-answer exposure is known. References carried
inside an authorized composite map are observations of that map, not a review
of another dated answer map. Phase 1's separate incidental editor-metadata log
was preserved unchanged.

An initial stale browser connection was restored by refreshing the tool session
and reconnecting to the same in-app tab. Later, browser security policy rejected
the Make-copy navigation for the experimental layout. No workaround was tried.
The optional fixed 8-tick sensitivity therefore has **no executed comparisons**.
The baseline layout/settings were retained; a read-only check confirmed its
original URL afterward. No fresh X access was needed for the selected retained
sources, and none is claimed. The stage's access-exposure-log.json records this
scope separately from historical source clocks.

## Checks and reproducibility

The [bounded checker](check_review.py) verifies frozen input hashes, ordering of
neutral captures before source access, authorized dates, original source bytes,
null timing, stable references, finite price intervals, all 19 comparison
alternatives, retained source conflicts, case/figure presence and Phase 1 artifact
hashes. It does not independently OCR screenshots or establish scientific validity.

```sh
python3 studies/29_verniman_level_reconstruction/phase2/check_review.py
python3 -m unittest discover -s scripts/tests -p test_check_registry.py
python3 scripts/check-agent-docs.py
```

The checker passed: **23 source entries, 21 original source paths hashed,
143 level occurrences, 2,717 all-family comparison rows, 61 Phase 1 artifacts
unchanged**. An earlier preservation check also confirmed 13 current Phase 1
source/settings/guide files match their saved snapshot; only the mutable study
README received a Phase 2 navigation addition.

Inventory generation uses standard-library Python and explicit manual readings.
Release selection used the existing locked environment without sync. The three
authored figures were rendered with the desktop bundled ReportLab/Sharp after
matplotlib was found absent; no package/environment lock was changed. All three
PNG figures were visually inspected for readable labels, correct source/reference
values and clipping. Source screenshots/full posts were not copied into tracked
figures. Exact commands, outputs and byte inventory are staged under
`work/29_verniman_level_reconstruction/phase2_20261030T222323Z/`.

Focused registry tests passed **35/35**; documentation checked **110 guides
with zero errors**. The explicit harness command also passed:

```sh
./scripts/check-workspace --check study-29-phase2-review --report work/29_verniman_level_reconstruction/phase2_20261030T222323Z/phase2-review-check.json
```

This check requires the explicit private stage and is excluded from every
automatic profile. Focused logs and the structured report retain the outcomes.
Eight Phase 2 maintained guides were added to the existing owner. Study navigation
metadata and generated indexes did not change, so metadata/navigation checks and
index regeneration were not selected. The broad numerical/default gate and
historical research were not rerun for this source-review/documentation phase.

## What remains uncertain

Pre-open delivery, exact source profile windows/feed/binning, true volume-at-price
versus any approximation, composite membership, HVE thresholds and causal PBT
anchors remain unidentified. Source conflicts remain separate observations;
after-close maps cannot repair earlier timing. Nearest-price comparisons do not
select targets or explain why a source reference was chosen. The
[Phase 3 specification](phase3-specification.md) distinguishes ready engineering
interfaces/manual ledgers from modules requiring more training evidence.

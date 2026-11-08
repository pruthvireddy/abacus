# Autopivot Levels - Daily — display and alternate-reference update

User-requested revision on 2026-10-30 New York. The primary 09:25 selector,
profile backend and N1/E1 rules are unchanged. The prior private indicator was
renamed **Autopivot Levels - Daily** and updated in place. Existing baseline,
Phase 1/2 records and the original v1 verification evidence remain preserved.

## Display

- Main pivot: purple, width 1; a main fallback retains its dashed style.
- One additional distinct prior-value reference: black, dotted, width 1.
- Both lines start at 09:25 and end at 16:00 New York by default.
- Plain small labels at the right endpoint, following the repository's VP Levels
  `label.style_none` presentation: `Pivot 7764.00`, `Alt YPOC 7772.00`.
  Detailed reasons and source identities remain in tooltips and optional diagnostics.
- Inputs → **Show diagnostic table** controls the table, default off. It was
  tested both on and off and left off in the saved chart. A separate compact
  incompatible-chart warning can still appear when the table is hidden.
- Inputs → **Show alternate / fallback level** defaults on. Strict mode suppresses
  fallback drawings, including the alternate. Daily retention removes both levels
  together; object limits allow two lines/labels for each of 100 retained days.

## Alternate policy

This is a descriptive prior-value fallback, not a claim that a second N1 edge
has been ranked as another primary pivot. Freeze price and reference identity
with the existing snapshot; do not recompute from later closes.

1. Behind a selected higher-auction E1 edge, use YVAH, then YPOC, then YVAL.
2. If the primary is YVAL, prefer YPOC, then YVAH.
3. If the primary is YVAH, prefer YPOC, then YVAL.
4. For the balanced YPOC primary, prefer the nearer distinct value boundary to P;
   an exact distance tie chooses the lower boundary.
5. Always skip a candidate equal to the primary. Missing required inputs or no
   distinct candidate leaves the alternate unavailable; never invent a price.

The unchanged three-date frozen inputs give these alternate references:

| Date | Main | Alternate | Alternate reference |
|---|---:|---:|---|
| 2026-10-01 | 7752 | 7772 | YPOC |
| 2026-10-02 | 7788 | 7724 | YVAH |
| 2026-10-05 | 7764 | 7772 | YPOC |

These three-date alternate values were calculated by the independent translated
helper from the retained v1 frozen inputs. New native verification focused on the
Oct 5 cutoff, display and post-cutoff invariance; it does not claim a repeated full
three-date Replay matrix for this revision.

## Verification and private save

- Native TradingView compile/save succeeded in the authenticated in-app browser.
- Oct 5: no main or alternate before the terminal confirmation; after confirmation,
  main 7764 and alternate YPOC 7772; both remained fixed after eight more five-minute
  steps into RTH while acceptance could change.
- Purple width 1 / black dotted width 1 and simple right-end labels observed.
- Table shown and hidden successfully; all frozen inputs and alternate identity
  visible when enabled. It was returned to hidden before the layout save.
- Reload retained private script name, attachment, settings, alternate enabled,
  diagnostic table disabled, and source. Clipboard readback uses CRLF; after
  normalizing only line endings, saved source exactly matches the delivered LF file.
- Saved private revision 3. Layout remains
  [Verniman Pivot Levels — Verification](https://www.tradingview.com/chart/isTi4G1i/).
- Initial focused study gate: **116 passed**, zero skips, including 21 new alternate
  tests. During the update, other working-tree study additions increased direct
  discovery to **180 tests**, all passing in the locked environment. A final
  registered-gate invocation was blocked by an unrelated newly referenced missing
  guide: `phase3/pine-implementation.md`; that registry entry was not changed.
  Existing primary-selector text is byte-identical to v1; its hash is retained.
- These tests and this feature do not establish Verniman source-method fidelity.
  Original candle-profile and feed/calendar limitations remain.

[Current Pine source](verniman_pivot_levels.pine), SHA-256 `22604477ef983021911320b255d0d08e937ab10c81f852ca25358fb972fd1a49`.
New evidence: `work/29_verniman_level_reconstruction/20261031T003557Z_autopivot_daily_display/` relative to the Abacus root, including
before/after sources, change contract, model tests, screenshots, saved settings,
primary-preservation check and artifact hashes. Earlier completed work evidence
was not overwritten. All requested update actions completed.

Final documentation check: blocked by the same unrelated missing maintained-guide reference; see retained log.

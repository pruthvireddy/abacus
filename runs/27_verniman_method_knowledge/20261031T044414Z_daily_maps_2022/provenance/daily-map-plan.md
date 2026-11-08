# Daily Map archive protocol

Protocol 1.4.0, extended 2026-10-31. Extend study 27 with a local Daily Map
subsection and separately frozen annual source archives, newest first.
This is source preservation, not a level dataset release or trading study.

## Authorized archive scopes

| Snapshot | Inclusive dates | Calendar records | Retained stage |
|---|---|---:|---|
| Original 2026 archive | January 1 through October 30, 2026 | 303 | `work/27_verniman_method_knowledge/20261031T030640Z_daily_maps_2026/` |
| 2025 extension | January 1 through December 31, 2025 | 365 | `work/27_verniman_method_knowledge/20261031T032348Z_daily_maps_2025/` |
| 2024 extension | January 1 through December 31, 2024 | 366 | `work/27_verniman_method_knowledge/20261031T034949Z_daily_maps_2024_r2/` |
| 2023 extension | January 1 through December 31, 2023 | 365 | `work/27_verniman_method_knowledge/20261031T043818Z_daily_maps_2023/` |
| 2022 extension | January 1 through December 31, 2022 | 365 | `work/27_verniman_method_knowledge/20261031T044414Z_daily_maps_2022/` |

The 2025 extension starts at the observed [December 31 map](https://verniman.blogspot.com/2008/12/good-bye-2025.html),
already preserved as the 2026 traversal boundary. Use the explicit reviewed 2025
capture manifest at
`data/raw/blogspot/verniman/html/20261021T001954Z_history_6118f516/collection_manifest.reviewed.json`
for hash-pinned source recovery and image reuse. Its metadata is a locator, not
authorization to modify the corresponding dataset. The 2026 source archive and
completed run remain immutable.

The 2024 extension starts at the observed [December 31, 2024 map](https://verniman.blogspot.com/2007/12/good-bye-2024.html),
preserved as the 2025 traversal boundary. Its explicit reviewed source manifest
is `data/raw/blogspot/verniman/html/20261021T003531Z_history_2b60d46b/collection_manifest.reviewed.json`.
Record all 366 days of this leap year, including February 29. Preserve completed
2025 and 2026 runs and readers unchanged. Current Daily Map navigation lists
annual snapshots in descending year order.

The initial 2024 attempt remains retained at
`work/27_verniman_method_knowledge/20261031T034949Z_daily_maps_2024/`.
A malformed image link in the October 30 article interrupted that attempt.
The fresh r2 execution records malformed request URLs as failures and uses only
the actual inline source URL as a qualified fallback, without guessing a repaired
full-size URL. The prior image inventory omitted this image; count actual article
image elements as well as prior retained records when auditing completeness.

The 2023 extension starts at the observed [December 29, 2023 map](https://verniman.blogspot.com/2006/12/last-dance.html),
preserved as the 2024 traversal boundary. Use the reviewed source manifest
`data/raw/blogspot/verniman/html/20261021T010315Z_history_a9716d20/collection_manifest.reviewed.json`
for hash-pinned recovery and image reuse. The requested range still includes all
365 days through December 31; the December 29 seed does not remove the two
end-of-year weekend dates from coverage. Keep the completed 2024, 2025 and 2026
readers and runs unchanged, with current year navigation in descending order.

The 2022 extension starts at the observed [December 30, 2022 map](https://verniman.blogspot.com/2005/12/final-day.html),
preserved as the 2023 boundary. Use
`data/raw/blogspot/verniman/html/20261021T012001Z_history_49cd90e5/collection_manifest.reviewed.json`
for pinned source recovery and image reuse. Current navigation jumps from May 16,
2022 to a body explicitly naming December 31, 2021; do not relabel that boundary
as 2022 or fill the substantial early-year gap with 2021 plans.

The explicit study input `daily-map-2022-date-overrides.json` pins source reviews,
supporting HTML identities, normalized article-body hashes and two bounded date
exceptions. It assigns the explicit 2021 boundary to 2021-12-31 and keeps the
stale ESZ21 Near ATHs insertion as separately qualified context, without a 2022
date. Require matching article text and month/day before applying either
exception, including during retained-source reconciliation. Record all 365
calendar dates, the early-year gap and the December 31 weekend gap. Retain every
actual image in the stale context, even where the earlier inventory omitted it.
The completed 2023–2026 archives remain unchanged.

## Scope and source identity

For the original 2026 scope, begin at the user's supplied
[October 30 map](https://verniman.blogspot.com/2009/10/ai-worries_0248886265.html).
For annual extensions, use the explicit observed boundary seed declared above.
Follow explicit Older Post links, retaining traversal order. Capture the official
sitemap index and its declared pages, and use their ordered locators to continue
after a missing link. Continue across the January boundary. Inspect the live site
in the in-app browser as needed. Do not construct daily URLs from titles or dates.

Recover missing live revisions from already retained, hash-verified local source
captures when available. Preserve their original capture times and identify these
as historical captures, not fresh observations. Keep old input bytes and all
published datasets unchanged. Probe known missing locators explicitly and log
failure; record every calendar date, including weekends and January 1.

Daily identity comes from the article's Outlook month/day, with the year anchored
to each snapshot's requested end date and decremented only across a clear
January/December boundary.
URL years, source update dates and image filename dates do not replace that text.
Retain duplicate dates, nonmonotonic dates and ambiguous/undated commentaries.
Capture time is not historical availability; no available-at claim is made.

## Retention and presentation

Stage each execution under its distinct retained stage above.
Retain compressed exact HTML responses, all article text and outbound links,
and every article image available at the source's linked or inline resolution.
Prefer the linked full image; if it fails, retain an explicitly qualified inline
rendition. Preserve original compressed image bytes without lossy resizing and
deduplicate by content hash. Do not archive unrelated sidebar graphics.

Provide an offline reader and Markdown navigation with year/month folders,
descending dates, per-day records, source links, provenance and a gap log.
Full source material stays in the retained ignored stage; completed run indexes
and inventories point to it. Do not mirror full articles/images into ordinary Git
history or publish externally. Do not alter the sealed October 23 method review.
The current study knowledge-base hub links both the frozen method and Daily Map.

## Acceptance and preservation

- Every scoped calendar date has a record; multiple posts per date remain separate.
- Traversal and sitemap discovery are recorded, with lower-boundary evidence.
- All source/image failures and recovered historical revisions are explicit.
- Exact source and payload hashes, capture times, executed commands, settings,
  code revision/dirty snapshot and environment identities are retained.
- Validate text extraction, local links, ordering, gzip round trips, image hashes,
  coverage counts and original input hashes. Review representative months and
  the latest/earliest day in the offline reader. No numerical suite applies.
- Run documentation, metadata and navigation checks for changed guidance/indexes.
  Any skipped or failing checks remain explicit.
- Seal a new unique run only after verification. Keep the retained stage as source
  evidence, not disposable cache. Future corrections use another archive run.

# Daily Map archive protocol

Protocol 1.0.0, authorized 2026-10-30. Extend study 27 with a local Daily Map
subsection covering 2026-10-30 through 2026-01-01 inclusive, newest first.
This is source preservation, not a level dataset release or trading study.

## Scope and source identity

Begin at the user's supplied [October 30 map](https://verniman.blogspot.com/2009/10/ai-worries_0248886265.html).
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
to October 30, 2026 and decremented only across a clear January/December boundary.
URL years, source update dates and image filename dates do not replace that text.
Retain duplicate dates, nonmonotonic dates and ambiguous/undated commentaries.
Capture time is not historical availability; no available-at claim is made.

## Retention and presentation

Stage under `work/27_verniman_method_knowledge/20261031T030640Z_daily_maps_2026/`.
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

- All 303 calendar dates have a record; multiple posts per date remain separate.
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

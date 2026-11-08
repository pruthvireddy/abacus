# Daily Map archive protocol

Protocol 1.11.0, extended 2026-10-31. Extend study 27 with a local Daily Map
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
| 2021 extension | January 1 through December 31, 2021 | 365 | `work/27_verniman_method_knowledge/20261031T051744Z_daily_maps_2021/` |
| 2020 extension | January 1 through December 31, 2020 | 366 | `work/27_verniman_method_knowledge/20261031T052904Z_daily_maps_2020_r3/` |
| 2019 extension | January 1 through December 31, 2019 | 365 | `work/27_verniman_method_knowledge/20261031T053752Z_daily_maps_2019/` |
| 2018 extension | January 1 through December 31, 2018 | 365 | `work/27_verniman_method_knowledge/20261031T054252Z_daily_maps_2018/` |
| 2017 extension | January 1 through December 31, 2017 | 365 | `work/27_verniman_method_knowledge/20261031T054828Z_daily_maps_2017/` |
| 2016 extension | January 1 through December 31, 2016 | 366 | `work/27_verniman_method_knowledge/20261031T141551Z_daily_maps_2016_r2/` |
| 2015 extension | January 1 through December 31, 2015 | 365 | `work/27_verniman_method_knowledge/20261031T143306Z_daily_maps_2015/` |

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

The 2021 extension starts at the observed [December 31, 2021 map](https://verniman.blogspot.com/2004/12/good-bye-2021.html),
preserved as the 2022 boundary. Use
`data/raw/blogspot/verniman/html/20261021T020716Z_history_fda74d29/collection_manifest.reviewed.json`
for pinned source recovery and image reuse. Record all 365 dates and cross below
January 1 into the explicit December 31, 2020 boundary.

`daily-map-2021-date-overrides.json` pins the independent supplement review for
Near ATHs and its October 18, 2021 source identity. Apply that reviewed date only
after body/hash verification; its present location in the 2022 navigation does
not change its 2021 classification. Preserve the completed 2022 archive's separate
context record unchanged. Jackson Hole II states the malformed date `08/276`;
retain it as undated source material rather than infer August 27. Keep all
completed 2022–2026 readers and runs unchanged.

The 2020 extension starts at the observed [December 31, 2020 map](https://verniman.blogspot.com/2003/12/new-years-eve.html),
preserved as the 2021 boundary. Use
`data/raw/blogspot/verniman/html/20261021T022151Z_history_ae7996e0/collection_manifest.reviewed.json`
for pinned source recovery and image reuse. Record all 366 dates, including
February 29, and cross below January 1 into the December 31, 2019 boundary.
Retain duplicate body dates and every actual article image element. On October 5,
both anchors target the first chart although the second inline image is a different
chart. Preserve the second actual inline rendition with an explicit source-link
qualification; do not guess a corrected full-size URL. Match rendered elements
by their inline identities before potentially shared anchor URLs. Source update
years and contract delivery years do not replace anchored body chronology. Keep
completed 2021–2026 readers and runs unchanged.

The initial 2020 attempt remains retained at
`work/27_verniman_method_knowledge/20261031T052904Z_daily_maps_2020/`.
Its restricted connection failed to resolve the source host and it recovered
historical pages from the pinned manifest. The unsealed r2 attempt at
`work/27_verniman_method_knowledge/20261031T052904Z_daily_maps_2020_r2/`
captured fresh pages and sitemaps before the October 5 source-link collision was
identified. The r3 execution preserves the distinct inline chart with corrected
image matching. Retain both earlier attempts separately; neither is a completed
2020 reader, and historical recoveries are not fresh source observations.

The 2019 extension starts at the observed [December 31, 2019 map](https://verniman.blogspot.com/2019/12/2019-is-over.html),
preserved as the 2020 boundary. Use the reviewed and dataset-pinned final source
manifest at
`data/raw/blogspot/verniman/html/20261021T024404Z_history_4004cb93/collection_manifest.final.json`.
Its source posts, dates and traversal are identical to the separately retained
reviewed manifest; final review additions retain more provenance without changing
the source bodies. Verify these original input bytes and source-image identities.
Record all 365 dates, including January 1 and end-of-month gaps, and cross below
January into the December 31, 2018 boundary. Preserve duplicate source dates;
deduplicate identical image bytes without losing distinct source references.
Keep completed 2020–2026 readers and runs unchanged.

The 2018 extension starts at the observed [December 31, 2018 map](https://verniman.blogspot.com/2018/12/2018-close.html),
preserved as the 2019 boundary. Use the reviewed and dataset-pinned final source
manifest at
`data/raw/blogspot/verniman/html/20261021T030325Z_history_6c02b819/collection_manifest.final.json`.
Its posts, dates and traversal match the separately retained reviewed manifest.
Record all 365 dates and cross below January into the December 29, 2017 boundary.
Preserve repeated source dates and every actual article image element, including
articles with fewer images. Source publication claims of 2001 and later update
claims do not replace independently reviewed, anchored body chronology. Do not
infer delivery contracts or change literal source text. Keep completed 2019–2026
readers and runs unchanged.

## Scope and source identity

The 2017 extension starts at the observed [December 29 map](https://verniman.blogspot.com/2017/12/goodbye-2017.html),
preserved as the 2018 boundary. Use the reviewed, dataset-pinned final source
manifest `data/raw/blogspot/verniman/html/20261021T033311Z_history_bccc6daf/collection_manifest.final.json`.
Its source records match the separately retained reviewed manifest. The current
source trail contains only 28 dated maps, November 20–December 29, and twelve
daily plans whose Outlook bodies omit month/day. Preserve these twelve as
undated; do not infer dates from November URLs, images or neighboring posts.

Record all 365 calendar dates, including December 30–31 and the substantial
early-year gap. No 2016 daily-map boundary is observed. Navigation exhausts at
the reviewed `vtp.html` terminal; capture the official sitemap index/pages and
account for the seed-to-terminal range without following unrelated sitemap
content past that observed terminal. The hash-pinned completion and chronology
reviews document earlier exhausted public-feed discovery. Exhaustion of current
sources does not establish historical completeness.

Five reviewed educational/platform records remain raw in the capture manifest's
`excluded_context_posts`, with their source images retained in the stage. They
do not become daily maps or the twelve undated daily plans. Exclusion requires
matching requested scope, verified review/source HTML identities and normalized
body hashes; dated or changed bodies are refused. Keep all completed 2018–2026
readers and runs unchanged.

The 2016 extension uses the reviewed historical archive collection at
`data/raw/blogspot/verniman/archive_html/20261021T041009Z_2016_review_00a94d4c/collection_manifest.final.json`,
pinned by dataset 12.0.0. Current navigation does not reach these sources. Preserve
the selected 160 archived records, January 5–December 1, as retained historical
observations rather than fresh live captures. No 2015 boundary or historical
full-year completeness is observed. The latest known original locator is
`https://verniman.blogspot.com/2016/12/outlook-1201.html`; record current checks
separately from the pinned archive discovery, navigation and failed attempts.

The study-local `capture_retained_daily_maps.py` verifies the explicit manifest
pin, review/source identities and title Outlook month/day with reviewed 2016 year
evidence. Preserve 135 exact HTML responses and 25 exactly selected archived Atom
entries. For feed entries, retain the original XML and selector/ordinal, and
identify the entry-only HTML wrapper as derived. Do not parse XML as an article
or replace literal source text with extracted numerical fields.

All 560 selected image elements have retained current-source responses whose
historical byte identity is unverified. Keep original response bytes, capture
times and that qualification visibly with each image; do not describe them as
verified 2016 image payloads. Store shared original feed XML once by content hash,
linked from every selected entry. Preserve the pinned collection's historical
failed attempts, duplicate/unselected revisions and excluded context as provenance.
Record all 366 calendar dates, including February 29 and source gaps. Keep all
completed 2017–2026 readers and runs unchanged.

The 2015 extension begins from explicit archived source locators, including the
indexed [December 31 outlook](https://web.archive.org/web/20160103040551id_/http://verniman.blogspot.com:80/2015/12/outlook-1231.html).
There is no existing 2015 dataset release to rebuild. Stage new discovery, paced
archive captures, source responses/headers, image retrievals and classification
under `work/27_verniman_method_knowledge/20261031T143306Z_daily_maps_2015_recovery/`.
Use the complete bounded CDX index and observed archive/home/feed navigation;
do not construct guessed daily URLs. Preserve failed attempts and later reused
pages as evidence without silently assigning their URL year as a source date.

Select daily plans from their actual archived Outlook/Opening title and body.
Use explicit title month/day plus independently reviewed historical year evidence;
do not turn intraday updates, closing notes, reviews or educational replacements
into morning maps merely because their URLs contain dates. Keep unresolved dates
and context separate. Retain every actual source image and qualify current-source
fallback bytes as historically unverified. Pin the reviewed new source collection
before adapting it into the final reader, retaining the original responses and
any exact entry selectors. Record all 365 dates and coverage limits; do not claim
historical completeness or a lower-year boundary without observed evidence.
Keep completed 2016–2026 readers and runs unchanged.

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


The initial unsealed 2016 candidate remains retained at
`work/27_verniman_method_knowledge/20261031T141551Z_daily_maps_2016/`.
The r2 execution keeps third-party context prose in source payloads rather than
run metadata; metadata retains its hash, byte count and pinned source locator.
No reader was built or run sealed from the initial candidate. Preserve it as
retained preparation evidence; do not confuse it with the completed r2 snapshot.

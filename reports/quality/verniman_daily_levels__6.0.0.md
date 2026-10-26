# Verniman chronological history 6.0.0

Declared interval: 2022-01-01 through 2022-12-31, inclusive. Retained post revisions: 159. Complete: 151; partial: 3; failed numeric extraction: 5. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 157. Extracted numeric level rows: 1367. Calendar dates without observed posts: 208.

Retained-post source coverage: HTML 159/159, Atom 159/159. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2022, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder headings, explicit Rollover week/note paragraphs and paragraphs that begin with the FOMC reminder text terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0, 2.0.0, 3.0.0, 4.0.0 and 5.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_parse_failed | 5 |
| contextual_price_outlier | 7 |
| contract_year_differs_from_session | 9 |
| different_branch_triggers | 5 |
| duplicate_outlook_date | 4 |
| operative_contract_header_conflict | 3 |
| other_contracts_mentioned | 7 |
| singular_multi_point_sequence | 5 |
| source_updated_date_differs | 81 |
| source_weekday_differs | 17 |
| stale_source_year_conflict | 1 |
| target_opposite_trigger_direction | 13 |

## Observed 2022 source-history boundary

The available contemporary 2022 plans span 2022-05-16 through 2022-12-30: 158 posts. The 159 retained rows also include 1 stale source-year body insertions, flagged and excluded from numeric extraction. The observed older-post navigation jumps from [2022-05-16](https://verniman.blogspot.com/2015/05/more-bounce.html) to a post explicitly describing [the 2021-12-31 session](https://verniman.blogspot.com/2004/12/good-bye-2021.html). The reviewed date for that older boundary is 2021-12-31; it is retained raw and excluded from the 2022 tables.

Thus January 1 through 2022-05-15 has no contemporary 2022 plan in the observed source sequence. The public-feed comparison and reciprocal boundary links qualify this coverage gap; they do not prove that deleted or inaccessible plans never existed. The original generic crawl assigned the post after this large month/day discontinuity to the wrong year. Its original ledger, inferred dates, source files and stop state remain retained. The separate chronology review supplies the explicit-year boundary selection; this publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. The original FileExistsError was an intentional local no-overwrite control stop to flush metadata, rather than a provider retrieval failure. Older context captured beyond the boundary remains raw and does not enter this release.

## Weekdays without a captured dated post (103)

2022-01-03, 2022-01-04, 2022-01-05, 2022-01-06, 2022-01-07, 2022-01-10, 2022-01-11, 2022-01-12, 2022-01-13, 2022-01-14, 2022-01-17, 2022-01-18, 2022-01-19, 2022-01-20, 2022-01-21, 2022-01-24, 2022-01-25, 2022-01-26, 2022-01-27, 2022-01-28, 2022-01-31, 2022-02-01, 2022-02-02, 2022-02-03, 2022-02-04, 2022-02-07, 2022-02-08, 2022-02-09, 2022-02-10, 2022-02-11, 2022-02-14, 2022-02-15, 2022-02-16, 2022-02-17, 2022-02-18, 2022-02-21, 2022-02-22, 2022-02-23, 2022-02-24, 2022-02-25, 2022-02-28, 2022-03-01, 2022-03-02, 2022-03-03, 2022-03-04, 2022-03-07, 2022-03-08, 2022-03-09, 2022-03-10, 2022-03-11, 2022-03-14, 2022-03-15, 2022-03-16, 2022-03-17, 2022-03-18, 2022-03-21, 2022-03-22, 2022-03-23, 2022-03-24, 2022-03-25, 2022-03-28, 2022-03-29, 2022-03-30, 2022-03-31, 2022-04-01, 2022-04-04, 2022-04-05, 2022-04-06, 2022-04-07, 2022-04-08, 2022-04-11, 2022-04-12, 2022-04-13, 2022-04-14, 2022-04-15, 2022-04-18, 2022-04-19, 2022-04-20, 2022-04-21, 2022-04-22, 2022-04-25, 2022-04-26, 2022-04-27, 2022-04-28, 2022-04-29, 2022-05-02, 2022-05-03, 2022-05-04, 2022-05-05, 2022-05-06, 2022-05-09, 2022-05-10, 2022-05-11, 2022-05-12, 2022-05-13, 2022-05-17, 2022-05-30, 2022-06-02, 2022-06-20, 2022-07-04, 2022-09-05, 2022-11-24, 2022-12-27

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2022-01-03 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-04 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-05 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-06 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-07 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-10 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-11 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-12 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-13 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-14 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-17 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-18 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-19 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-20 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-21 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-24 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-25 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-26 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-27 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-28 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-01-31 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-01 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-02 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-03 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-04 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-07 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-08 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-09 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-10 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-11 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-14 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-15 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-16 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-17 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-18 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-21 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-22 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-23 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-24 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-25 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-02-28 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-01 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-02 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-03 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-04 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-07 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-08 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-09 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-10 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-11 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-14 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-15 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-16 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-17 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-18 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-21 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-22 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-23 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-24 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-25 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-28 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-29 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-30 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-03-31 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-01 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-04 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-05 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-06 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-07 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-08 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-11 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-12 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-13 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-14 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-15 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-18 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-19 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-20 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-21 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-22 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-25 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-26 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-27 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-28 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-04-29 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-02 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-03 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-04 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-05 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-06 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-09 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-10 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-11 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-12 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-13 | No captured dated post in this interval | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) |
| 2022-05-17 | 2022-05-16: [More bounce ](https://verniman.blogspot.com/2015/05/more-bounce.html) | 2022-05-18: [Retail losses](https://verniman.blogspot.com/2005/05/retail-losses.html) |
| 2022-05-30 | 2022-05-27: [Lower PCE](https://verniman.blogspot.com/2011/05/lower-pce.html) | 2022-05-31: [Inflation concerns](https://verniman.blogspot.com/2010/05/inflation-concerns.html) |
| 2022-06-02 | 2022-06-01: [ADP report](https://verniman.blogspot.com/2010/06/adp-report.html); [June start](https://verniman.blogspot.com/2012/06/june-start.html) | 2022-06-03: [Jobs Report](https://verniman.blogspot.com/2010/06/jobs-report.html) |
| 2022-06-20 | 2022-06-17: [Quad witching](https://verniman.blogspot.com/2010/06/quad-witching.html) | 2022-06-21: [Dead cat](https://verniman.blogspot.com/2014/06/dead-cat.html) |
| 2022-07-04 | 2022-07-01: [Second Half](https://verniman.blogspot.com/2005/07/second-half.html) | 2022-07-05: [Slump persists](https://verniman.blogspot.com/2012/07/slump-persists.html) |
| 2022-09-05 | 2022-09-02: [Jobs Report](https://verniman.blogspot.com/2012/09/jobs-report.html) | 2022-09-06: [Everyone's back](https://verniman.blogspot.com/2022/09/everyones-back.html) |
| 2022-11-24 | 2022-11-23: [FOMC Minutes](https://verniman.blogspot.com/2005/11/fomc-minutes.html) | 2022-11-25: [Black Friday](https://verniman.blogspot.com/2005/11/black-friday.html) |
| 2022-12-27 | 2022-12-26: [Holiday Week](https://verniman.blogspot.com/2005/12/holiday-week.html) | 2022-12-28: [Tesla in tatters](https://verniman.blogspot.com/2005/12/tesla-in-tatters.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (2 groups)

| Stated date | Source posts |
|---|---|
| 2022-06-01 | [ADP report](https://verniman.blogspot.com/2010/06/adp-report.html); [June start](https://verniman.blogspot.com/2012/06/june-start.html) |
| 2022-10-18 | [Near ATHs](https://verniman.blogspot.com/2004/10/near-aths.html); [Real rally, or not?](https://verniman.blogspot.com/2005/10/real-rally-or-not.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (8 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2022-05-20 | partial | [Friday bounce](https://verniman.blogspot.com/2012/05/friday-bounce.html) | branch_parse_failed: unassigned or unrecognised numeric level: ONH 3949050 and HVEs 3979-4020-4056. |
| 2022-09-12 | failed | [Rollover Day](https://verniman.blogspot.com/2005/09/rollover-day.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |
| 2022-10-10 | partial | [Q3 Earnings](https://verniman.blogspot.com/2005/10/q3-earnings.html) | branch_parse_failed: ambiguous singular multi-price sequence: HVE 3703-24-40 |
| 2022-10-18 | failed | [Near ATHs](https://verniman.blogspot.com/2004/10/near-aths.html) | stale_source_year_conflict: The anchored 2022 date conflicts with the permitted source delivery-contract year; numeric extraction refused and the post retained. |
| 2022-11-02 | failed | [FOMC Day](https://verniman.blogspot.com/2005/11/fomc-day.html) | branch_parse_failed: unassigned or unrecognised numeric level: YLOD; branch_parse_failed: unassigned or unrecognised numeric level: YLOD |
| 2022-11-04 | partial | [Jobs Report](https://verniman.blogspot.com/2005/11/jobs-report.html) | branch_parse_failed: ambiguous singular multi-price sequence: HVE 3752-39-24 |
| 2022-12-12 | failed | [Rollover Week](https://verniman.blogspot.com/2005/12/rollover-week.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |
| 2022-12-13 | failed | [CPI data](https://verniman.blogspot.com/2005/12/outlook-1212-stock-futures-roared.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

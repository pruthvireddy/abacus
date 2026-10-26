# Verniman chronological history 4.0.0

Declared interval: 2024-01-01 through 2024-12-31, inclusive. Retained post revisions: 251. Complete: 248; partial: 1; failed numeric extraction: 2. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 247. Extracted numeric level rows: 2178. Calendar dates without observed posts: 119.

Retained-post source coverage: HTML 251/251, Atom 251/251. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2024, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder headings, explicit Rollover week/note paragraphs and paragraphs that begin with the FOMC reminder text terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0, 2.0.0 and 3.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_parse_failed | 3 |
| contextual_price_outlier | 13 |
| contract_missing | 1 |
| contract_year_differs_from_session | 10 |
| different_branch_triggers | 6 |
| duplicate_outlook_date | 8 |
| other_contracts_mentioned | 6 |
| singular_multi_point_sequence | 1 |
| source_updated_date_differs | 6 |
| source_weekday_differs | 55 |
| target_opposite_trigger_direction | 17 |

## Weekdays without a captured dated post (15)

2024-01-01, 2024-01-15, 2024-02-02, 2024-02-19, 2024-03-29, 2024-05-13, 2024-05-27, 2024-06-19, 2024-07-05, 2024-07-16, 2024-07-19, 2024-09-02, 2024-11-06, 2024-11-28, 2024-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

## Duplicate stated dates (4 groups)

| Stated date | Source posts |
|---|---|
| 2024-02-01 | [Bounce back](https://verniman.blogspot.com/2007/02/bounce-back.html); [Jobs Report](https://verniman.blogspot.com/2007/02/jobs-report.html) |
| 2024-07-15 | [Retail Sales](https://verniman.blogspot.com/2007/07/retail-sales.html); [Trump effect](https://verniman.blogspot.com/2007/07/trump-effect.html) |
| 2024-07-18 | [Global outage](https://verniman.blogspot.com/2007/07/global-outage.html); [Tech sell-off](https://verniman.blogspot.com/2007/07/tech-sell-off.html) |
| 2024-11-05 | [Election day](https://verniman.blogspot.com/2007/11/election-day.html); [Trump wins](https://verniman.blogspot.com/2007/11/trump-wins.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (3 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2024-02-09 | failed | [CPI Revision](https://verniman.blogspot.com/2007/02/cpi-revision.html) | branch_parse_failed: unassigned or unrecognised numeric level: ON-VAH; branch_parse_failed: unassigned or unrecognised numeric level: ON-VAH |
| 2024-05-01 | partial | [FOMC Day](https://verniman.blogspot.com/2007/05/fomc-day.html) | branch_parse_failed: conjoined prices require an explicit plural source label: GAP 5004 and 4963 |
| 2024-12-11 | failed | [CPI report](https://verniman.blogspot.com/2007/12/cpi-report.html) | contract_missing: No unambiguous source ES contract was found; no numeric extraction. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

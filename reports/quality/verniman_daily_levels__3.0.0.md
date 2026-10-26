# Verniman chronological history 3.0.0

Declared interval: 2025-01-01 through 2025-12-31, inclusive. Retained post revisions: 246. Complete: 244; partial: 1; failed numeric extraction: 1. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 242. Extracted numeric level rows: 1896. Calendar dates without observed posts: 123.

Retained-post source coverage: HTML 246/246, Atom 246/246. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2025, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets; singular two-endpoint ranges are zones. Numbered notes and Reminder headings terminate plan branches. Explicit postfix support/resistance/magnet labels, observed mixed-case SoC compounds and HVE-1yrPOC preserve their source wording. The nonstandard ONl label retains its exact case and an explicit warning.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 and 2.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_parse_failed | 1 |
| contextual_price_outlier | 8 |
| contract_year_differs_from_session | 11 |
| different_branch_triggers | 4 |
| duplicate_outlook_date | 8 |
| nonstandard_source_label | 1 |
| operative_contract_header_conflict | 1 |
| other_contracts_mentioned | 4 |
| singular_multi_point_sequence | 3 |
| source_updated_date_differs | 99 |
| source_weekday_differs | 49 |
| target_opposite_trigger_direction | 25 |

## Weekdays without a captured dated post (19)

2025-01-01, 2025-01-03, 2025-01-09, 2025-01-20, 2025-01-21, 2025-01-22, 2025-01-23, 2025-01-24, 2025-02-17, 2025-04-18, 2025-05-26, 2025-06-19, 2025-06-20, 2025-07-04, 2025-07-07, 2025-09-01, 2025-10-16, 2025-11-27, 2025-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

## Duplicate stated dates (4 groups)

| Stated date | Source posts |
|---|---|
| 2025-01-02 | [Rocky Start](https://verniman.blogspot.com/2008/01/rocky-start.html); [Welcome 2025!](https://verniman.blogspot.com/2008/01/welcome-2025.html) |
| 2025-06-18 | [FOMC day](https://verniman.blogspot.com/2008/06/fomc-day.html); [Triple Witching](https://verniman.blogspot.com/2008/06/triple-witching.html) |
| 2025-07-08 | [Tariff talk](https://verniman.blogspot.com/2008/07/tariff-talk.html); [Less fear](https://verniman.blogspot.com/2025/07/less-fear.html) |
| 2025-10-15 | [BofA earnings](https://verniman.blogspot.com/2008/10/bofa-earnings.html); [Tech earnings](https://verniman.blogspot.com/2008/10/tech-earnings.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (2 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2025-06-13 | partial | [Israel-Iran](https://verniman.blogspot.com/2008/06/israel-iran.html) | branch_parse_failed: branch direction/action does not unambiguously match its side |
| 2025-12-15 | failed | [Rollover week](https://verniman.blogspot.com/2008/12/rollover-week.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

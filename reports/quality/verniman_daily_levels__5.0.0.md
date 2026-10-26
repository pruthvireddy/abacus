# Verniman chronological history 5.0.0

Declared interval: 2023-01-01 through 2023-12-31, inclusive. Retained post revisions: 248. Complete: 244; partial: 1; failed numeric extraction: 3. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 245. Extracted numeric level rows: 2191. Calendar dates without observed posts: 120.

Retained-post source coverage: HTML 248/248, Atom 248/248. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2023, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder headings, explicit Rollover week/note paragraphs and paragraphs that begin with the FOMC reminder text terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0, 2.0.0, 3.0.0 and 4.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| abbreviated_decimal_zone | 1 |
| branch_parse_failed | 3 |
| contextual_price_outlier | 3 |
| contract_year_differs_from_session | 14 |
| different_branch_triggers | 6 |
| duplicate_outlook_date | 6 |
| missing_level_separator | 1 |
| nonstandard_target_delimiter | 1 |
| operative_contract_assignment_ambiguous | 1 |
| operative_contract_header_conflict | 1 |
| other_contracts_mentioned | 10 |
| singular_multi_point_sequence | 5 |
| source_updated_date_differs | 9 |
| source_weekday_differs | 33 |
| target_opposite_trigger_direction | 13 |
| weekend_stated_outlook_date | 1 |

## Weekdays without a captured dated post (16)

2023-01-02, 2023-01-16, 2023-02-01, 2023-02-03, 2023-02-07, 2023-02-20, 2023-04-06, 2023-04-07, 2023-05-29, 2023-06-19, 2023-07-04, 2023-08-15, 2023-09-04, 2023-10-13, 2023-11-23, 2023-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

## Weekend stated dates (1 posts)

| Stated date | Source | Source-claimed updated timestamp |
|---|---|---|
| 2023-10-14 | [Banks Q3](https://verniman.blogspot.com/2006/10/outlook-1014-stock-futures-are-slightly.html) | 2023-10-13T09:17:57.596-04:00 |

The source-stated dates remain unchanged even when update metadata names another day. Calendar weekends are descriptive; no exchange-session eligibility is inferred.

## Duplicate stated dates (3 groups)

| Stated date | Source posts |
|---|---|
| 2023-02-02 | [After FOMC](https://verniman.blogspot.com/2006/02/fomc-day.html); [Jobs Report](https://verniman.blogspot.com/2006/02/jobs-report.html) |
| 2023-04-05 | [ADP report](https://verniman.blogspot.com/2006/04/adp-report.html); [Jobless Claims](https://verniman.blogspot.com/2006/04/jobless-claims.html) |
| 2023-08-14 | [China slowdown](https://verniman.blogspot.com/2006/08/china-slowdown.html); [Consumer week](https://verniman.blogspot.com/2006/08/consumer-week.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (4 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2023-01-25 | failed | [More earnings](https://verniman.blogspot.com/2006/01/more-earnings.html) | branch_parse_failed: unassigned or unrecognised numeric level: ONL; branch_parse_failed: unassigned or unrecognised numeric level: ONL |
| 2023-02-23 | partial | [After Minutes](https://verniman.blogspot.com/2006/02/after-minutes.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4016 |
| 2023-03-13 | failed | [Rollover Day](https://verniman.blogspot.com/2006/03/svb-mess.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |
| 2023-06-12 | failed | [Rollover day](https://verniman.blogspot.com/2006/06/rollover-day.html) | operative_contract_assignment_ambiguous: The source heading and an unqualified future-tense quoting statement name different contracts. The quote cites currently greater volume without a conditional future term; the operative contract for these prices remains ambiguous. Both branch texts, heading and quote are retained, but numeric extraction is refused. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

# Verniman chronological history 7.0.0

Declared interval: 2021-01-01 through 2021-12-31, inclusive. Retained post revisions: 251. Complete: 229; partial: 19; failed numeric extraction: 3. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 246. Extracted numeric level rows: 1937. Calendar dates without observed posts: 119.

Retained-post source coverage: HTML 251/251, Atom 251/251. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2021, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder headings, explicit Rollover week/note paragraphs and paragraphs that begin with the FOMC reminder text terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 6.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_parse_failed | 19 |
| compound_lis_source_label | 101 |
| contextual_price_outlier | 2 |
| contract_year_differs_from_session | 14 |
| different_branch_triggers | 17 |
| duplicate_outlook_date | 8 |
| future_intraday_contract_switch | 1 |
| ledger_body_date_mismatch | 1 |
| nonstandard_source_label | 3 |
| operative_contract_assignment_ambiguous | 1 |
| other_contracts_mentioned | 7 |
| past_contract_switch_header_conflict | 1 |
| session_date_unresolved | 1 |
| singular_multi_point_sequence | 5 |
| slash_separated_plural_points | 2 |
| source_updated_date_differs | 14 |
| source_weekday_differs | 47 |
| target_opposite_trigger_direction | 9 |

## Collection chronology review

The new older-link traversal is anchored to the explicit final trading session of 2021. Sixty-two prior context captures retain their original timestamps and are assigned 2021 dates from their visible month/day chronology; the prior generic crawler's 2022 dates are not adopted.

A fresh public-feed comparison discovers a detached Near ATHs body stating Outlook 10/18, Monday and ESZ21. The separately pinned review corroborates October 18, 2021 with neighboring source context. Its current navigation among 2022 posts and 2025 update claim remain recorded; its date method is explicitly supplemental rather than older-link chronology.

Outlook 08/276 is retained as malformed and undated, with no numeric extraction or guessed August 27 date. Distinct source revisions sharing dates remain separate, and calendar gaps are retrieval observations rather than proof of no historical publication.

Supplemental image captures retain explicit full-size post-body links, including extensionless and legacy-host URLs missed by the frozen capture helper. Response bytes, headers, timestamps and failures remain pinned separately; no chart-only levels are inferred.

Original publication and update claims remain separate from session dates and source capture times. Every available_at remains null; historical pre-open availability is unverified.

The reviewed older boundary [the 2020-12-31 session](https://verniman.blogspot.com/2003/12/new-years-eve.html) is retained raw and excluded from the 2021 tables.

The original source captures and traversal ledger remain retained. This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts.

## Weekdays without a captured dated post (15)

2021-01-01, 2021-01-18, 2021-02-15, 2021-03-30, 2021-04-02, 2021-05-13, 2021-05-31, 2021-06-11, 2021-07-05, 2021-08-27, 2021-09-06, 2021-09-29, 2021-11-09, 2021-11-25, 2021-12-24

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2021-01-01 | No captured dated post in this interval | 2021-01-04: [2021 First session](https://verniman.blogspot.com/2004/01/2021-first-session.html) |
| 2021-01-18 | 2021-01-15: [Earnings Season](https://verniman.blogspot.com/2004/01/earnings-season.html) | 2021-01-19: [Yellen Confirmation](https://verniman.blogspot.com/2004/01/yellen-confirmation.html) |
| 2021-02-15 | 2021-02-12: [Positive Week](https://verniman.blogspot.com/2004/02/positive-week.html) | 2021-02-16: [Record High](https://verniman.blogspot.com/2004/02/record-high_16.html) |
| 2021-03-30 | 2021-03-29: [Archegos collapse](https://verniman.blogspot.com/2004/03/archegos-collapse.html); [Yields again](https://verniman.blogspot.com/2004/03/yields-again.html) | 2021-03-31: [ADP Report](https://verniman.blogspot.com/2004/03/adp-report_31.html) |
| 2021-04-02 | 2021-04-01: [Jobless Claims](https://verniman.blogspot.com/2004/04/jobless-claims.html) | 2021-04-05: [After NFP](https://verniman.blogspot.com/2004/04/after-nfp.html) |
| 2021-05-13 | 2021-05-12: [Inflation data](https://verniman.blogspot.com/2004/05/inflation-data.html) | 2021-05-14: [More inflation](https://verniman.blogspot.com/2004/05/more-inflation.html); [Turning around](https://verniman.blogspot.com/2004/05/turning-around.html) |
| 2021-05-31 | 2021-05-28: [Inflation again](https://verniman.blogspot.com/2004/05/inflation-again.html) | 2021-06-01: [June start](https://verniman.blogspot.com/2004/06/june-start.html) |
| 2021-06-11 | 2021-06-10: [More Inflation](https://verniman.blogspot.com/2004/06/more-inflation.html) | 2021-06-14: [Busy Week](https://verniman.blogspot.com/2004/06/busy-week.html) |
| 2021-07-05 | 2021-07-02: [Jobs Report](https://verniman.blogspot.com/2004/07/jobs-report.html) | 2021-07-06: [Short Week](https://verniman.blogspot.com/2004/07/short-week.html) |
| 2021-08-27 | 2021-08-26: [Jackson Hole I](https://verniman.blogspot.com/2004/08/jackson-hole-1.html) | 2021-08-30: [New Record](https://verniman.blogspot.com/2004/08/new-record_30.html) |
| 2021-09-06 | 2021-09-03: [Jobs Report](https://verniman.blogspot.com/2004/09/jobs-report.html) | 2021-09-07: [After Labor Day](https://verniman.blogspot.com/2004/09/after-labor-day.html) |
| 2021-09-29 | 2021-09-28: [Powell testimony](https://verniman.blogspot.com/2004/09/powell-testimony.html); [Seeking Bias](https://verniman.blogspot.com/2004/09/seeking-bias.html) | 2021-09-30: [Rough Month](https://verniman.blogspot.com/2004/09/rough-month.html) |
| 2021-11-09 | 2021-11-08: [Bill boost](https://verniman.blogspot.com/2004/11/bill-boost.html); [PPI still high](https://verniman.blogspot.com/2004/11/ppi-still-high.html) | 2021-11-10: [CPI soars](https://verniman.blogspot.com/2004/11/cpi-soars.html) |
| 2021-11-25 | 2021-11-24: [Jobless Claims](https://verniman.blogspot.com/2004/11/jobless-claims_24.html) | 2021-11-26: [Black Friday](https://verniman.blogspot.com/2004/11/black-friday.html) |
| 2021-12-24 | 2021-12-23: [Santa Rally?](https://verniman.blogspot.com/2004/12/santa-rally.html) | 2021-12-27: [Santa in the House](https://verniman.blogspot.com/2004/12/santa-in-house.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (4 groups)

| Stated date | Source posts |
|---|---|
| 2021-03-29 | [Archegos collapse](https://verniman.blogspot.com/2004/03/archegos-collapse.html); [Yields again](https://verniman.blogspot.com/2004/03/yields-again.html) |
| 2021-05-14 | [More inflation](https://verniman.blogspot.com/2004/05/more-inflation.html); [Turning around](https://verniman.blogspot.com/2004/05/turning-around.html) |
| 2021-09-28 | [Powell testimony](https://verniman.blogspot.com/2004/09/powell-testimony.html); [Seeking Bias](https://verniman.blogspot.com/2004/09/seeking-bias.html) |
| 2021-11-08 | [Bill boost](https://verniman.blogspot.com/2004/11/bill-boost.html); [PPI still high](https://verniman.blogspot.com/2004/11/ppi-still-high.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (22 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2021-01-11 | partial | [New Impeachment](https://verniman.blogspot.com/2004/01/new-impeachment.html) | branch_parse_failed: conjoined prices require an explicit plural source label: GAP 3745 and 3724 |
| 2021-03-12 | failed | [Yield fears](https://verniman.blogspot.com/2004/03/yield-fears.html) | operative_contract_assignment_ambiguous: The source says I start quoting another contract as its delivery month increases to equal volume, while retaining a different heading. The transition phase and operative contract for the captured prices remain ambiguous; both branches and heading are retained but numeric extraction is refused. No active-switch or timing claim is inferred. |
| 2021-04-27 | partial | [New Record](https://verniman.blogspot.com/2004/04/new-record_27.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4184 |
| 2021-04-28 | partial | [FOMC Day](https://verniman.blogspot.com/2004/04/fomc-day.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4183 |
| 2021-04-29 | partial | [Big Tech Q1](https://verniman.blogspot.com/2004/04/big-tech-q1.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4202 |
| 2021-07-23 | partial | [Rally goes on](https://verniman.blogspot.com/2004/07/rally-goes-on.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4375 |
| 2021-07-26 | partial | [Busy week](https://verniman.blogspot.com/2004/07/busy-week.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4385 |
| 2021-08-11 | partial | [CPI data](https://verniman.blogspot.com/2004/08/outlook-0811-stock-futures-point-to.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH-ATH and PBTs 4443/4448. |
| 2021-08-13 | partial | [New Record](https://verniman.blogspot.com/2021/08/outlook-0813-stock-futures-point-to.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4456 |
| 2021-08-20 | partial | [Losing week](https://verniman.blogspot.com/2004/08/losing-week.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4411 |
| 2021-08-24 | partial | [New Record](https://verniman.blogspot.com/2004/08/new-record.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4486 |
| 2021-08-25 | partial | [Neutral Day](https://verniman.blogspot.com/2004/08/neutral-day.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4486 |
| 2021-08-30 | partial | [New Record](https://verniman.blogspot.com/2004/08/new-record_30.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4510 |
| 2021-09-20 | partial | [China Crisis](https://verniman.blogspot.com/2004/09/china-crisis.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4363 |
| 2021-10-12 | partial | [House vote](https://verniman.blogspot.com/2004/10/house-vote.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4363 |
| 2021-10-25 | partial | [Tech Earnings](https://verniman.blogspot.com/2004/10/tech-earnings.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4546 |
| 2021-10-26 | partial | [New ATH](https://verniman.blogspot.com/2004/10/new-ath.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4573 |
| 2021-11-15 | partial | [Back to ATH](https://verniman.blogspot.com/2004/11/back-to-ath.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4690 |
| 2021-12-06 | partial | [Monday pause](https://verniman.blogspot.com/2004/12/monday-pause.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4552 |
| 2021-12-07 | partial | [Less fearful](https://verniman.blogspot.com/2004/12/less-fearful.html) | branch_parse_failed: unassigned or unrecognised numeric level: 4645 |
| 2021-12-10 | failed | [Inflation report](https://verniman.blogspot.com/2004/12/inflation-report.html) | past_contract_switch_header_conflict: The source says it started quoting another contract after the NYSE opening bell while retaining a different contract heading. The captured body's contract assignment is inconsistent; both branch texts remain but numeric extraction is refused. The statement does not establish pre-open availability or an execution timestamp. |
| Unresolved | failed | [Jackson Hole II](https://verniman.blogspot.com/2004/08/jackson-hole-ii.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

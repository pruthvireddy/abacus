# Verniman chronological history 8.0.0

Declared interval: 2020-01-01 through 2020-12-31, inclusive. Retained post revisions: 251. Complete: 245; partial: 2; failed numeric extraction: 4. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 248. Extracted numeric level rows: 2197. Calendar dates without observed posts: 118.

Retained-post source coverage: HTML 251/251, Atom 251/251. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2020, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder headings, explicit Rollover week/note paragraphs and paragraphs that begin with the FOMC reminder text terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Plan A/B are source letters, not fixed economic sides. In this release economic side follows the explicit above+buy or below+sell direction/action pair, with contradictory explicit confirmation wording refused. The original A/B texts are retained in source_plan_a_text/source_plan_b_text, and source_plan_branch on levels plus bullish_source_plan_branch/bearish_source_plan_branch on outlooks/summary preserve the original letter. Duplicate source letters, contradictory or missing directional instructions, and two branches for the same side remain raw with issues; no side is invented from alphabetical position. These additive fields and the new side-assignment policy apply only to 8.0.0; earlier releases remain byte-identical.

Source letters reversed relative to A-bullish/B-bearish shorthand: 76 retained posts. This describes source ordering and does not change economic direction or source text.

Additional 2020 source syntax retains compound LIS labels sharing one explicit price or zone, including POC/LVN and the observed hyphenated or spaced HVE/value combinations. Exact RTH Limit Down and RTH limit targets remain qualified source_market_limit_claim observations, without independent exchange-limit or execution validation. An unqualified present I start quoting another contract while the heading names a different contract causes numeric refusal because transition phase is ambiguous. The prospective wording I'll start quoting new /ESH21 after the Opening Bell retains the heading and a future switch warning.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 7.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_direction_ambiguous | 3 |
| branch_duplicated | 1 |
| branch_missing | 5 |
| branch_parse_failed | 1 |
| compound_lis_source_label | 371 |
| contextual_price_outlier | 5 |
| contract_year_differs_from_session | 13 |
| different_branch_triggers | 61 |
| duplicate_outlook_date | 6 |
| future_intraday_contract_switch | 1 |
| operative_contract_assignment_ambiguous | 1 |
| operative_contract_header_conflict | 1 |
| other_contracts_mentioned | 7 |
| singular_multi_point_sequence | 12 |
| source_market_limit_claim | 2 |
| source_plan_letters_reversed | 76 |
| source_updated_date_differs | 197 |
| source_weekday_differs | 31 |
| target_opposite_trigger_direction | 17 |

## Collection chronology review

The original older-link traversal is anchored to the body explicitly describing the final trading session of 2020. The retained December 31 seed preserves original source captures and timestamps; newly visited posts receive fresh captures. Older 2019 boundary evidence remains raw and is excluded from 2020 tables.

All 366 calendar dates remain in coverage. Duplicate source-stated dates and weekday disagreements are retained without correcting dates from prose, event context, publication metadata or update claims. Absences describe observed retrieval coverage rather than proof of no historical post.

Pandemic-era 2020 bodies bearing May 2021 batch-update claims retain those claims without changing their session year. Source dates follow anchored body chronology and source-context review, not update year or contract delivery year alone.

In 2020 original Plan A can be bearish and Plan B bullish. The new release preserves A/B text and source-letter fields separately from side, which requires consistent explicit above/buy or below/sell wording. Missing, contradictory or duplicated assignments remain source text with issues and no guessed numeric rows.

Full-size source images are retained with exact response bytes, URLs, headers, capture times and hashes. Supplemental records account for any explicit source image links missed by the frozen capture helper; no chart-only levels are inferred.

Source publication/update claims remain separate from session dates and capture times. Every available_at remains null with historical_availability_unverified; no pre-open timing is inferred.

The reviewed older boundary [the 2019-12-31 session](https://verniman.blogspot.com/2019/12/2019-is-over.html) is retained raw and excluded from the 2020 tables.

The original source captures and traversal ledger remain retained. This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. In this 2020 collection, source-claimed updates may be in 2021; metadata years do not reassign retained body dates.

## Weekdays without a captured dated post (14)

2020-01-01, 2020-01-17, 2020-01-20, 2020-02-17, 2020-03-24, 2020-04-10, 2020-05-15, 2020-05-25, 2020-06-03, 2020-06-16, 2020-07-03, 2020-09-07, 2020-11-26, 2020-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2020-01-01 | No captured dated post in this interval | 2020-01-02: [Welcome 2020](https://verniman.blogspot.com/2020/01/welcome-2020.html) |
| 2020-01-17 | 2020-01-16: [Phase Two](https://verniman.blogspot.com/2020/01/phase-two.html) | 2020-01-21: [Lower Open](https://verniman.blogspot.com/2020/01/lower-open.html) |
| 2020-01-20 | 2020-01-16: [Phase Two](https://verniman.blogspot.com/2020/01/phase-two.html) | 2020-01-21: [Lower Open](https://verniman.blogspot.com/2020/01/lower-open.html) |
| 2020-02-17 | 2020-02-14: [Retail Sales](https://verniman.blogspot.com/2020/02/retail-sales.html) | 2020-02-18: [Apple effect](https://verniman.blogspot.com/2020/02/apple-effect.html) |
| 2020-03-24 | 2020-03-23: [FED support](https://verniman.blogspot.com/2020/03/fed-support.html) | 2020-03-25: [Stimulus Deal](https://verniman.blogspot.com/2020/03/stimulus-deal.html) |
| 2020-04-10 | 2020-04-09: [Jobless Claims](https://verniman.blogspot.com/2020/04/jobless-claims_9.html) | 2020-04-13: [Crude Oil Cut](https://verniman.blogspot.com/2020/04/crude-oil-cut.html) |
| 2020-05-15 | 2020-05-14: [Jobless Claims](https://verniman.blogspot.com/2020/05/jobless-claims_14.html); [Retail Sales](https://verniman.blogspot.com/2020/05/retail-sales.html) | 2020-05-18: [Vaccine Hope](https://verniman.blogspot.com/2020/05/vaccine-hope.html) |
| 2020-05-25 | 2020-05-22: [Memorial Day](https://verniman.blogspot.com/2020/05/memorial-day.html) | 2020-05-26: [NYSE reopens](https://verniman.blogspot.com/2020/05/nyse-reopens.html) |
| 2020-06-03 | 2020-06-02: [ADP Report](https://verniman.blogspot.com/2020/06/adp-report.html); [Value Transition](https://verniman.blogspot.com/2020/06/value-transition.html) | 2020-06-04: [Jobless Claims](https://verniman.blogspot.com/2020/06/jobless-claims.html) |
| 2020-06-16 | 2020-06-15: [Retail Sales](https://verniman.blogspot.com/2020/06/retail-sales.html); [Second Wave](https://verniman.blogspot.com/2020/06/second-wave.html) | 2020-06-17: [Powell Day2](https://verniman.blogspot.com/2020/06/powell-day2.html) |
| 2020-07-03 | 2020-07-02: [Jobs Report](https://verniman.blogspot.com/2020/07/jobs-report.html) | 2020-07-06: [Rally again](https://verniman.blogspot.com/2020/07/rally-again.html) |
| 2020-09-07 | 2020-09-04: [Jobs Report](https://verniman.blogspot.com/2020/09/jobs-report.html) | 2020-09-08: [Tesla Snub](https://verniman.blogspot.com/2020/09/tesla-snub.html) |
| 2020-11-26 | 2020-11-25: [Jobless Claims](https://verniman.blogspot.com/2003/11/jobless-claims_25.html) | 2020-11-27: [Black Friday](https://verniman.blogspot.com/2003/11/black-friday.html) |
| 2020-12-25 | 2020-12-24: [Christmas Eve](https://verniman.blogspot.com/2003/12/christmas-eve.html) | 2020-12-28: [Santa Checks](https://verniman.blogspot.com/2003/12/santa-checks.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (3 groups)

| Stated date | Source posts |
|---|---|
| 2020-05-14 | [Jobless Claims](https://verniman.blogspot.com/2020/05/jobless-claims_14.html); [Retail Sales](https://verniman.blogspot.com/2020/05/retail-sales.html) |
| 2020-06-02 | [ADP Report](https://verniman.blogspot.com/2020/06/adp-report.html); [Value Transition](https://verniman.blogspot.com/2020/06/value-transition.html) |
| 2020-06-15 | [Retail Sales](https://verniman.blogspot.com/2020/06/retail-sales.html); [Second Wave](https://verniman.blogspot.com/2020/06/second-wave.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (6 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2020-03-09 | failed | [World Chaos](https://verniman.blogspot.com/2020/03/world-chaos.html) | branch_direction_ambiguous: Source Plan A: missing explicit buy/sell target clause; retain source text without a numeric side assignment.; branch_direction_ambiguous: Source Plan B: missing explicit buy/sell target clause; retain source text without a numeric side assignment.; branch_missing: No unique labelled plan branch was found.; branch_missing: No unique labelled plan branch was found. |
| 2020-03-18 | partial | [Limit Down](https://verniman.blogspot.com/2020/03/limit-down_18.html) | branch_direction_ambiguous: Source Plan B: source direction/action pair is contradictory; retain source text without a numeric side assignment.; branch_missing: No unique labelled plan branch was found. |
| 2020-04-16 | failed | [Jobless Claims](https://verniman.blogspot.com/2020/04/jobless-claims_16.html) | branch_duplicated: Multiple source Plan A branches have the same letter; no direction assignment or numeric extraction for that letter.; branch_missing: No unique labelled plan branch was found.; branch_missing: No unique labelled plan branch was found. |
| 2020-07-24 | partial | [Cold War](https://verniman.blogspot.com/2020/07/cold-war.html) | branch_parse_failed: conjoined prices require an explicit plural source label: GAP 3183 and 3177 |
| 2020-09-10 | failed | [Rollover begins](https://verniman.blogspot.com/2020/09/jobless-claims_10.html) | operative_contract_header_conflict: The source explicitly says it is quoting another contract today, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |
| 2020-09-11 | failed | [Rollover Day](https://verniman.blogspot.com/2020/09/rollover-day.html) | operative_contract_assignment_ambiguous: The source says I start quoting another contract without a conditional future qualifier while retaining a different heading. The transition phase and operative contract for the captured prices remain ambiguous; both branches and heading stay retained, but numeric extraction is refused. No pre-open availability or execution timestamp is established. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

# Verniman chronological history 9.0.0

Declared interval: 2019-01-01 through 2019-12-31, inclusive. Retained post revisions: 248. Complete: 239; partial: 5; failed numeric extraction: 4. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 246. Extracted numeric level rows: 2263. Calendar dates without observed posts: 119.

Retained-post source coverage: HTML 248/248, Atom 248/248. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2019, and each body's Outlook M/D. Delivery-contract year is retained separately. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder/Tips/Basics/Quotes/Notice headings, explicit Rollover week/note/starts, Expiration Week, When VIX climbs above and FOMC reminder paragraph openings terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Plan A/B are source letters, not fixed economic sides. In this release economic side follows the explicit above+buy or below+sell direction/action pair (including exact be/become a buyer/seller wording, retained with source_nominal_action_wording), with contradictory explicit confirmation wording refused. The original A/B texts are retained in source_plan_a_text/source_plan_b_text, and source_plan_branch on levels plus bullish_source_plan_branch/bearish_source_plan_branch on outlooks/summary preserve the original letter. Duplicate source letters, contradictory or missing directional instructions, and two branches for the same side remain raw with issues; no side is invented from alphabetical position. This release retains the additive source-letter fields and direction-assignment policy introduced in 8.0.0; all earlier releases remain byte-identical.

Source letters reversed relative to A-bullish/B-bearish shorthand: 77 retained posts. This describes source ordering and does not change economic direction or source text.

The source phrases be a buyer, become a buyer, be a seller and become a seller are explicit directional actions, paired with exactly one consistent above/below direction. Source nominal wording remains in both plan text and a source_nominal_action_wording issue. Today's Economic Calendar and subsequent Disclaimer, Questions and Glossary headings terminate plan extraction before calendar numbers. Additional supported source syntax retains compound LIS labels sharing one explicit price or zone, including POC/LVN and the observed hyphenated or spaced HVE/value combinations. Exact RTH Limit Down and RTH limit targets remain qualified source_market_limit_claim observations, without independent exchange-limit or execution validation. An unqualified present I start quoting another contract while the heading names a different contract causes numeric refusal because transition phase is ambiguous. Prospective opening-bell switches, including preposed after the bell and future-tense since NYSE opening bell wording, retain the heading and a future switch warning. The exact mixed-case HVE Tariffs SoC label and parenthesized ETH annotation retain source text and explicit warnings; no source correction or session eligibility is inferred. A single full numeric trigger point without a source label is retained with a null label and unlabelled_trigger_price warning. Bare ranges/lists and unpriced source labels remain unparsed; the opposite branch never supplies a missing label or price.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 7.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_duplicated | 3 |
| branch_missing | 6 |
| branch_parse_failed | 7 |
| compound_lis_source_label | 182 |
| contract_year_differs_from_session | 11 |
| different_branch_triggers | 139 |
| duplicate_outlook_date | 4 |
| future_intraday_contract_switch | 2 |
| nonstandard_source_label | 3 |
| other_contracts_mentioned | 8 |
| singular_multi_point_sequence | 7 |
| source_level_session_qualifier | 1 |
| source_nominal_action_wording | 34 |
| source_plan_letters_reversed | 77 |
| source_updated_date_differs | 248 |
| source_weekday_differs | 35 |
| target_opposite_trigger_direction | 6 |
| unlabelled_trigger_price | 90 |

## Collection chronology review

The original older-link traversal is anchored to the body explicitly describing the final trading session of 2019. The retained December 31 seed preserves original source captures and timestamps; newly visited posts receive fresh captures. Older 2018 boundary evidence remains raw and is excluded from 2019 tables.

All 365 calendar dates remain in coverage. Duplicate source-stated dates and weekday disagreements are retained without correcting dates from prose, event context, publication metadata or update claims. Absences describe observed retrieval coverage rather than proof of no historical post.

Source publication and update claims can disagree with body chronology. The independent feed reconciliation retains every discovered candidate and classification, including explicit feed exhaustion, without assigning a session year from metadata alone.

In 2019 original Plan A can be bearish and Plan B bullish. The new release preserves A/B text and source-letter fields separately from side, which requires consistent explicit above/buy or below/sell wording, including supported be/become a buyer/seller instructions. Missing, contradictory or duplicated assignments remain source text with issues and no guessed numeric rows.

An exact single numeric trigger without a source level name retains its stated price with source_label null and an unlabelled_trigger_price warning; no HVE/YVAL label is invented. Bare ranges/lists and ambiguous prices remain unsupported. This nullable-label policy is specific to version9.0.0.

Full-size source images are retained with exact response bytes, URLs, headers, capture times and hashes. Supplemental records account for any explicit source image links missed by the frozen capture helper; no chart-only levels are inferred.

Source publication/update claims remain separate from session dates and capture times. Every available_at remains null with historical_availability_unverified; no pre-open timing is inferred.

The reviewed older boundary [the 2018-12-31 session](https://verniman.blogspot.com/2018/12/2018-close.html) is retained raw and excluded from the 2019 tables.

The original source captures and traversal ledger remain retained. This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. In this 2019 collection, source-claimed updates may be from later years; metadata years do not reassign retained body dates.

## Weekdays without a captured dated post (15)

2019-01-01, 2019-01-21, 2019-02-18, 2019-04-19, 2019-05-27, 2019-06-12, 2019-06-18, 2019-07-04, 2019-07-09, 2019-07-12, 2019-08-20, 2019-08-23, 2019-09-02, 2019-11-28, 2019-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2019-01-01 | No captured dated post in this interval | 2019-01-02: [2019 Start](https://verniman.blogspot.com/2019/01/2019-start.html) |
| 2019-01-21 | 2019-01-18: [Fake News](https://verniman.blogspot.com/2019/01/fake-news.html) | 2019-01-22: [Global Concern](https://verniman.blogspot.com/2019/01/global-concern.html) |
| 2019-02-18 | 2019-02-15: [Trade Talks](https://verniman.blogspot.com/2019/02/trade-talks_15.html) | 2019-02-19: [Trade Talks](https://verniman.blogspot.com/2019/02/trade-talks_19.html) |
| 2019-04-19 | 2019-04-18: [Mueller Report](https://verniman.blogspot.com/2019/04/mueller-report.html) | 2019-04-22: [Red Monday](https://verniman.blogspot.com/2019/04/red-monday.html) |
| 2019-05-27 | 2019-05-24: [May Resigns](https://verniman.blogspot.com/2019/05/may-resigns.html) | 2019-05-28: [Not Ready](https://verniman.blogspot.com/2019/05/not-ready.html) |
| 2019-06-12 | 2019-06-11: [Trump comments](https://verniman.blogspot.com/2019/06/trump-comments.html) | 2019-06-13: [Oil Spikes](https://verniman.blogspot.com/2019/06/turning-back.html) |
| 2019-06-18 | 2019-06-17: [FOMC begins](https://verniman.blogspot.com/2019/06/fomc-begins.html); [FOMC Week](https://verniman.blogspot.com/2019/06/fomc-week.html) | 2019-06-19: [FOMC day](https://verniman.blogspot.com/2019/06/fomc-day.html) |
| 2019-07-04 | 2019-07-03: [Early Close](https://verniman.blogspot.com/2019/07/early-close.html) | 2019-07-05: [Job Growth](https://verniman.blogspot.com/2019/07/job-growth.html) |
| 2019-07-09 | 2019-07-08: [Markets Retreat](https://verniman.blogspot.com/2019/07/markets-retreat.html) | 2019-07-10: [Powell's Day](https://verniman.blogspot.com/2019/07/fed-speakers.html) |
| 2019-07-12 | 2019-07-11: [Dovish FED](https://verniman.blogspot.com/2019/07/dovish-fed.html) | 2019-07-15: [Q2 earnings](https://verniman.blogspot.com/2019/07/q2-earnings.html) |
| 2019-08-20 | 2019-08-19: [FED's Week](https://verniman.blogspot.com/2019/08/feds-week.html) | 2019-08-21: [FOMC Minutes](https://verniman.blogspot.com/2019/08/fomc-minutes.html) |
| 2019-08-23 | 2019-08-22: [Jackson Hole I](https://verniman.blogspot.com/2019/08/jackson-hole-i.html); [Jackson Hole II](https://verniman.blogspot.com/2019/08/jackson-hole-ii.html) | 2019-08-26: [China Call](https://verniman.blogspot.com/2019/08/china-call.html) |
| 2019-09-02 | 2019-08-30: [Strong Gains](https://verniman.blogspot.com/2019/08/strong-gains.html) | 2019-09-03: [China tariffs](https://verniman.blogspot.com/2019/09/china-tariffs.html) |
| 2019-11-28 | 2019-11-27: [More Rally](https://verniman.blogspot.com/2019/11/more-rally.html) | 2019-11-29: [Black Friday](https://verniman.blogspot.com/2019/11/black-friday.html) |
| 2019-12-25 | 2019-12-24: [Christmas Eve](https://verniman.blogspot.com/2019/12/christmas-eve.html) | 2019-12-26: [Santa Rally](https://verniman.blogspot.com/2019/12/santa-rally.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (2 groups)

| Stated date | Source posts |
|---|---|
| 2019-06-17 | [FOMC begins](https://verniman.blogspot.com/2019/06/fomc-begins.html); [FOMC Week](https://verniman.blogspot.com/2019/06/fomc-week.html) |
| 2019-08-22 | [Jackson Hole I](https://verniman.blogspot.com/2019/08/jackson-hole-i.html); [Jackson Hole II](https://verniman.blogspot.com/2019/08/jackson-hole-ii.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (9 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2019-01-31 | partial | [After FOMC](https://verniman.blogspot.com/2019/01/after-fomc.html) | branch_parse_failed: ambiguous abbreviated decimal endpoint |
| 2019-02-12 | partial | [Avert Shutdown](https://verniman.blogspot.com/2019/02/avert-shutdown.html) | branch_parse_failed: source label has no assigned explicit numeric level: YHOD |
| 2019-02-13 | partial | [Sliding Deadline](https://verniman.blogspot.com/2019/02/sliding-deadline.html) | branch_parse_failed: source label has no assigned explicit numeric level: YHOD |
| 2019-05-21 | failed | [Rebound mode](https://verniman.blogspot.com/2002/05/rebound-mode.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH 2863 LVN 2867 HVE-GBT 2873 and YHOD.; branch_parse_failed: source label has no assigned explicit numeric level: ONL 2846.25 LVN 2843 HVE 2837 and YLOD. |
| 2019-08-16 | partial | [Half Way](https://verniman.blogspot.com/2019/08/half-way.html) | branch_parse_failed: conjoined prices require an explicit plural source label: PBT 2900 and 2907 |
| 2019-10-30 | failed | [FOMC Day](https://verniman.blogspot.com/2019/10/fomc-day.html) | branch_duplicated: Multiple source Plan A branches have the same letter; no direction assignment or numeric extraction for that letter.; branch_missing: No unique labelled plan branch was found.; branch_missing: No unique labelled plan branch was found. |
| 2019-11-26 | partial | [New Records](https://verniman.blogspot.com/2019/11/new-records.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and ATH 3145. |
| 2019-12-02 | failed | [New Record](https://verniman.blogspot.com/2019/12/new-record.html) | branch_duplicated: Multiple source Plan A branches have the same letter; no direction assignment or numeric extraction for that letter.; branch_missing: No unique labelled plan branch was found.; branch_missing: No unique labelled plan branch was found. |
| 2019-12-03 | failed | [Unreliable List](https://verniman.blogspot.com/2019/12/unreliable-list.html) | branch_duplicated: Multiple source Plan A branches have the same letter; no direction assignment or numeric extraction for that letter.; branch_missing: No unique labelled plan branch was found.; branch_missing: No unique labelled plan branch was found. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

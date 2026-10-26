# Verniman chronological history 11.0.0

Declared interval: 2017-01-01 through 2017-12-31, inclusive. Retained post revisions: 40. Complete: 25; partial: 2; failed numeric extraction: 13. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 28. Extracted numeric level rows: 174. Calendar dates without observed posts: 337.

Retained-post source coverage: HTML 40/40, Atom 40/40. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, with December 31, 2017 as the inclusive calendar upper bound, the December 29 seed explicitly stating the final trading day of 2017, and each dated body's Outlook M/D. Delivery-contract year is retained separately. Exact one-digit ES contract suffix 7 or 8 denotes delivery year 2017 or permitted late-year 2018 within this independently anchored collection, with the source spelling retained and a single_digit_source_contract warning; no session date is inferred from it. Generic /ES Value headings with no explicit delivery contract retain ES source prices with contract null and source_contract_unspecified warning; explicit present quoting claims may establish a source contract, while ambiguous mentions cause numeric refusal. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder/Tips/Basics/Quotes/Notice headings, explicit Rollover week/note/starts, Expiration Week, When VIX climbs above and FOMC reminder paragraph openings terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Plan A/B/C are source letters, not fixed economic sides. In this release economic side follows the explicit above+buy or below+sell direction/action pair, including exact be/become a buyer/seller and optional try to wording. The separately qualified below+bearish internals+try to lean on one full price+towards labelled-target scenario also maps to bearish without asserting an explicit sell order. Contradictory explicit confirmation wording is refused. The original A/B/C texts are retained in source_plan_a_text/source_plan_b_text/source_plan_c_text, and source_plan_branch on levels plus bullish_source_plan_branch/bearish_source_plan_branch on outlooks/summary preserve the original letter. Duplicate source letters, contradictory or missing directional instructions, and two branches for the same side remain raw with issues; no side is invented from alphabetical position. This release retains the additive source-letter fields and direction-assignment policy introduced in 8.0.0; all earlier releases remain byte-identical.

Source letters reversed relative to A-bullish/B-bearish shorthand: 9 retained posts. This describes source ordering and does not change economic direction or source text.

The source phrases be a buyer, become a buyer, be a seller and become a seller are explicit directional actions, paired with exactly one consistent above/below direction. Source nominal wording remains in both plan text and a source_nominal_action_wording issue. Today's Economic Calendar and subsequent Disclaimer, Questions and Glossary headings terminate plan extraction before calendar numbers. Additional supported source syntax retains compound LIS labels sharing one explicit price or zone, including POC/LVN and the observed hyphenated or spaced HVE/value combinations. Exact RTH Limit Down and RTH limit targets remain qualified source_market_limit_claim observations, without independent exchange-limit or execution validation. An unqualified present I start quoting another contract while the heading names a different contract causes numeric refusal because transition phase is ambiguous. Prospective opening-bell switches, including preposed after the bell and future-tense since NYSE opening bell wording, retain the heading and a future switch warning. The exact mixed-case HVE Tariffs SoC label and parenthesized ETH/ON annotation retain source text and explicit warnings; no source correction or session eligibility is inferred. A single full numeric trigger point without a source label is retained with a null label and unlabelled_trigger_price warning. Bare ranges/lists and unpriced source labels remain unparsed; the opposite branch never supplies a missing label or price.

2017 source attribution retains source_plan_c_text and preserves C as a possible numeric source letter, while neutral A/B/C branches remain verbatim with issues. Literal ESM7/ESU7/ESZ7 and late-year ESH8 codes retain their one-digit spelling; their delivery year is qualified by the separately anchored 2017 chronology and permitted delivery-year policy. Generic /ES Value bodies with no explicit contract anywhere retain source ES prices with contract null, product ES and source_contract_unspecified. A directly stated present quoting claim, including the exact observed I still quoting wording, can identify an exact delivery contract with source_contract_from_explicit_quoting; ambiguous generic contract mentions remain null and contribute no numeric rows. No delivery contract is inferred from source images, neighboring sessions or price levels. Nullable labels remain limited to exact unlabelled trigger points; nullable delivery contracts are validated only against generic source parents and required warnings.

The source sometimes uses try to buy/sell or be/become a buyer/seller with an ancillary leaning on, above, below or around price/zone before towards. Those execution references stay in source_execution_reference issues and unchanged scenarios rather than replacing the initial conditional threshold or becoming extra targets. Exact quoted Look above/below and fail and Failure to take out/breakdown explanatory tails remain in source_branch_annotation, including their labels/prices/timing, rather than producing extra target rows. A narrowly supported try to lean on clause has no explicit sell order: its source scenario is classified bearish only with one conditional below direction, explicit bearish internals, one full leaning price and a towards labelled-target list, retaining source_lean_on_wording. Leaning zones/lists, contradictory or absent confirmations and ambiguous target prices remain refused. Explicit plural full point lists may use spaces, with space_separated_plural_points; singular or abbreviated space lists remain unsupported. Exact observed Edge/edge/Edge-LIS/Edge-LVN/HGap spellings and ON annotations retain source text and warnings.

2017 ancillary leaning-on references support at most three stated source price components with one full first price, bounded integer/full-price or two-digit decimal suffix components, and an optional and full-price or and edge full-price component. They remain unchanged source text and source_execution_reference issues only; no ancillary price is expanded or stored as a threshold or target. The conditional trigger and towards-delimited labelled target list remain independently validated. Missing source target prices and ambiguous singular target lists remain refused. Undated daily bodies retain session_date null and no numeric rows; neither publication metadata, permalinks nor image dates supply a guessed session date.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 10.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_parse_failed | 2 |
| different_branch_triggers | 2 |
| ledger_body_date_mismatch | 12 |
| nonstandard_source_label | 3 |
| operative_contract_assignment_ambiguous | 1 |
| other_contracts_mentioned | 1 |
| session_date_unresolved | 12 |
| single_digit_source_contract | 1 |
| source_branch_annotation | 52 |
| source_contract_from_explicit_quoting | 1 |
| source_contract_unspecified | 39 |
| source_execution_reference | 52 |
| source_nominal_action_wording | 52 |
| source_plan_letters_reversed | 9 |
| source_updated_date_differs | 28 |
| source_weekday_differs | 4 |

## Collection chronology review

The retained Outlook 12/29 seed explicitly states that today is the final trading day of 2017. This corroborates the prior descending chronology. The requested calendar ends December 31; no December 31 post is assumed. Original seed capture clocks remain unchanged and newly visited posts have fresh HTML, Atom and image captures.

The original navigation visits 45 posts and exhausts at vtp.html with no Older Post link. No dated 2016 daily-plan boundary is observed. traversal_reached_lower_boundary remains false. Independent complete current public-feed discovery captures 2207 entries through an exact empty next-page probe and reconciles every visited body and all 40 daily candidates.

Forty daily-plan bodies are selected: 28 state valid month/day values and 12 November-context Outlook bodies omit month/day. The latter keep session_date null, full source text and issues; no numeric extraction or metadata/permalink/image/neighbor-date repair is permitted. Five educational/platform records stay retained raw as explicitly excluded context.

All 365 requested calendar dates appear in coverage, with 232 weekdays and 105 weekends lacking a dated captured plan. No duplicate stated dates are observed. Earlier months have no current dated source plans; observed absence and exhausted current sources do not establish that no historical post existed or that all original 2017 content survives.

Preserve original A/B/C text and source letters separately from economic side. Direction requires consistent explicit source wording. Exact unlabelled numeric trigger points may retain a null source label with warning; targets require explicit labels and prices. Missing target prices, ambiguous assignments and unresolved dates remain text/issues without guessed numeric rows.

Generic ES Value does not identify a delivery contract. Retain qualified exact ES levels with contract null and an explicit warning where appropriate. Present still-quoting claims may identify the literal contract; ambiguous rollout transitions do not. Literal single-digit codes retain source spelling and never determine session dates.

Ancillary leaning-on price/range/list references stay unchanged in scenario text and source_execution_reference issues. They do not replace conditional triggers, become extra targets or supply missing target prices. Only bounded observed reference syntax is supported, and labelled target clauses remain independently validated.

All full-size image anchors, response bytes, URLs, headers, capture times and hashes are reconciled, including retained educational context. No chart-only levels are inferred.

All 40 selected publication claims carry year 2000; 39 update claims are from 2019 and one from 2020. Keep raw, UTC and Eastern source claims separate from session dates and capture clocks. Every available_at remains null with historical_availability_unverified; no pre-open availability is inferred. All ten prior releases remain unchanged.

The original source captures and traversal ledger remain retained. This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. In this 2017 collection, source-claimed updates may be from later years; metadata years do not reassign retained body dates.

## Weekdays without a captured dated post (232)

2017-01-02, 2017-01-03, 2017-01-04, 2017-01-05, 2017-01-06, 2017-01-09, 2017-01-10, 2017-01-11, 2017-01-12, 2017-01-13, 2017-01-16, 2017-01-17, 2017-01-18, 2017-01-19, 2017-01-20, 2017-01-23, 2017-01-24, 2017-01-25, 2017-01-26, 2017-01-27, 2017-01-30, 2017-01-31, 2017-02-01, 2017-02-02, 2017-02-03, 2017-02-06, 2017-02-07, 2017-02-08, 2017-02-09, 2017-02-10, 2017-02-13, 2017-02-14, 2017-02-15, 2017-02-16, 2017-02-17, 2017-02-20, 2017-02-21, 2017-02-22, 2017-02-23, 2017-02-24, 2017-02-27, 2017-02-28, 2017-03-01, 2017-03-02, 2017-03-03, 2017-03-06, 2017-03-07, 2017-03-08, 2017-03-09, 2017-03-10, 2017-03-13, 2017-03-14, 2017-03-15, 2017-03-16, 2017-03-17, 2017-03-20, 2017-03-21, 2017-03-22, 2017-03-23, 2017-03-24, 2017-03-27, 2017-03-28, 2017-03-29, 2017-03-30, 2017-03-31, 2017-04-03, 2017-04-04, 2017-04-05, 2017-04-06, 2017-04-07, 2017-04-10, 2017-04-11, 2017-04-12, 2017-04-13, 2017-04-14, 2017-04-17, 2017-04-18, 2017-04-19, 2017-04-20, 2017-04-21, 2017-04-24, 2017-04-25, 2017-04-26, 2017-04-27, 2017-04-28, 2017-05-01, 2017-05-02, 2017-05-03, 2017-05-04, 2017-05-05, 2017-05-08, 2017-05-09, 2017-05-10, 2017-05-11, 2017-05-12, 2017-05-15, 2017-05-16, 2017-05-17, 2017-05-18, 2017-05-19, 2017-05-22, 2017-05-23, 2017-05-24, 2017-05-25, 2017-05-26, 2017-05-29, 2017-05-30, 2017-05-31, 2017-06-01, 2017-06-02, 2017-06-05, 2017-06-06, 2017-06-07, 2017-06-08, 2017-06-09, 2017-06-12, 2017-06-13, 2017-06-14, 2017-06-15, 2017-06-16, 2017-06-19, 2017-06-20, 2017-06-21, 2017-06-22, 2017-06-23, 2017-06-26, 2017-06-27, 2017-06-28, 2017-06-29, 2017-06-30, 2017-07-03, 2017-07-04, 2017-07-05, 2017-07-06, 2017-07-07, 2017-07-10, 2017-07-11, 2017-07-12, 2017-07-13, 2017-07-14, 2017-07-17, 2017-07-18, 2017-07-19, 2017-07-20, 2017-07-21, 2017-07-24, 2017-07-25, 2017-07-26, 2017-07-27, 2017-07-28, 2017-07-31, 2017-08-01, 2017-08-02, 2017-08-03, 2017-08-04, 2017-08-07, 2017-08-08, 2017-08-09, 2017-08-10, 2017-08-11, 2017-08-14, 2017-08-15, 2017-08-16, 2017-08-17, 2017-08-18, 2017-08-21, 2017-08-22, 2017-08-23, 2017-08-24, 2017-08-25, 2017-08-28, 2017-08-29, 2017-08-30, 2017-08-31, 2017-09-01, 2017-09-04, 2017-09-05, 2017-09-06, 2017-09-07, 2017-09-08, 2017-09-11, 2017-09-12, 2017-09-13, 2017-09-14, 2017-09-15, 2017-09-18, 2017-09-19, 2017-09-20, 2017-09-21, 2017-09-22, 2017-09-25, 2017-09-26, 2017-09-27, 2017-09-28, 2017-09-29, 2017-10-02, 2017-10-03, 2017-10-04, 2017-10-05, 2017-10-06, 2017-10-09, 2017-10-10, 2017-10-11, 2017-10-12, 2017-10-13, 2017-10-16, 2017-10-17, 2017-10-18, 2017-10-19, 2017-10-20, 2017-10-23, 2017-10-24, 2017-10-25, 2017-10-26, 2017-10-27, 2017-10-30, 2017-10-31, 2017-11-01, 2017-11-02, 2017-11-03, 2017-11-06, 2017-11-07, 2017-11-08, 2017-11-09, 2017-11-10, 2017-11-13, 2017-11-14, 2017-11-15, 2017-11-16, 2017-11-17, 2017-11-23, 2017-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2017-01-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-01-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-02-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-29 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-03-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-04-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-29 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-05-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-29 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-06-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-07-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-29 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-08-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-21 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-22 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-28 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-09-29 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-04 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-05 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-11 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-12 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-18 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-19 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-20 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-23 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-24 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-25 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-26 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-27 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-30 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-10-31 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-01 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-02 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-03 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-06 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-07 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-08 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-09 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-10 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-13 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-14 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-15 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-16 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-17 | No captured dated post in this interval | 2017-11-20: [Holiday Week](https://verniman.blogspot.com/2017/11/holiday-week.html) |
| 2017-11-23 | 2017-11-22: [FED Minutes](https://verniman.blogspot.com/2017/11/fed-minutes.html) | 2017-11-24: [Black Friday](https://verniman.blogspot.com/2017/11/black-friday.html) |
| 2017-12-25 | 2017-12-22: [Before Christmas](https://verniman.blogspot.com/2017/12/before-christmas.html) | 2017-12-26: [After Christmas](https://verniman.blogspot.com/2017/12/after-christmas.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Source extent and undated daily plans (12 posts)

Currently captured dated bodies span 2017-11-20 through 2017-12-29; this is source extent rather than a claim of full-year historical completeness. Undated daily bodies remain in outlooks and the viewing summary with null session_date and zero numeric levels. Source timestamp claims, permalinks and image dates do not supply missing body dates. Full-calendar gaps describe dated source observations only.

| Source | Source-claimed published timestamp | Source-claimed updated timestamp | Qualification |
|---|---|---|---|
| [.](https://verniman.blogspot.com/2017/11/fomc-day.html) | 2000-11-01T07:52:00.000-05:00 | 2020-02-02T11:20:23.074-05:00 | Session date unresolved; numeric extraction refused. |
| [Game of Thrones](https://verniman.blogspot.com/2017/11/game-of-thrones.html) | 2000-11-06T07:54:00.000-05:00 | 2019-05-30T15:56:00.979-04:00 | Session date unresolved; numeric extraction refused. |
| [Global Rally](https://verniman.blogspot.com/2017/11/global-rally.html) | 2000-11-07T08:23:00.000-05:00 | 2019-05-30T15:56:01.047-04:00 | Session date unresolved; numeric extraction refused. |
| [House votes taxes](https://verniman.blogspot.com/2017/11/house-votes-taxes.html) | 2000-11-16T08:53:00.000-05:00 | 2019-05-30T15:56:00.851-04:00 | Session date unresolved; numeric extraction refused. |
| [Inflation Data](https://verniman.blogspot.com/2017/11/inflation-data.html) | 2000-11-15T08:24:00.000-05:00 | 2019-05-30T15:56:00.785-04:00 | Session date unresolved; numeric extraction refused. |
| [Tuesday Worries](https://verniman.blogspot.com/2017/11/outlook-strong-german-economic-growth.html) | 2000-11-14T09:02:00.000-05:00 | 2019-05-30T15:56:01.103-04:00 | Session date unresolved; numeric extraction refused. |
| [Tax Plan Advances](https://verniman.blogspot.com/2017/11/tax-bill-advances.html) | 2000-11-17T08:14:00.000-05:00 | 2019-05-30T15:56:01.096-04:00 | Session date unresolved; numeric extraction refused. |
| [Tax Plan Delay](https://verniman.blogspot.com/2017/11/tax-plan-delay.html) | 2000-11-13T09:00:00.000-05:00 | 2019-05-30T15:56:00.912-04:00 | Session date unresolved; numeric extraction refused. |
| [Tax Reform Delay](https://verniman.blogspot.com/2017/11/tax-reform-delay.html) | 2000-11-10T08:41:00.000-05:00 | 2019-05-30T15:56:01.068-04:00 | Session date unresolved; numeric extraction refused. |
| [The Powell Fed](https://verniman.blogspot.com/2017/11/the-powell-fed.html) | 2000-11-02T08:08:00.000-05:00 | 2019-05-30T15:56:00.949-04:00 | Session date unresolved; numeric extraction refused. |
| [Trump on China](https://verniman.blogspot.com/2017/11/trump-on-china.html) | 2000-11-08T08:45:00.000-05:00 | 2019-05-30T15:56:01.037-04:00 | Session date unresolved; numeric extraction refused. |
| [US-China deal](https://verniman.blogspot.com/2017/11/us-china-deal.html) | 2000-11-09T08:35:00.000-05:00 | 2019-05-30T15:56:00.919-04:00 | Session date unresolved; numeric extraction refused. |

These are retained daily scenarios with missing body month/day, not additional dated sessions or duplicate-date cases. Their source timestamp claims remain unverified historical availability metadata.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (0 groups)

None.

## Partial or failed numeric extraction (15 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2017-12-08 | failed | [Jobs Report](https://verniman.blogspot.com/2017/12/jobs-report.html) | operative_contract_assignment_ambiguous: A generic /ES Value heading and other contract mentions do not uniquely establish an operative contract. No first-token or front-month assignment is made; numeric extraction is refused. |
| 2017-12-15 | partial | [Tax Reform](https://verniman.blogspot.com/2017/12/tax-reform.html) | branch_parse_failed: conjoined prices require an explicit plural source label: LVN 2665-2669 and 2673 |
| 2017-12-29 | partial | [Goodbye 2017](https://verniman.blogspot.com/2017/12/goodbye-2017.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2702-2707 |
| Unresolved | failed | [.](https://verniman.blogspot.com/2017/11/fomc-day.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Game of Thrones](https://verniman.blogspot.com/2017/11/game-of-thrones.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Global Rally](https://verniman.blogspot.com/2017/11/global-rally.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [House votes taxes](https://verniman.blogspot.com/2017/11/house-votes-taxes.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Inflation Data](https://verniman.blogspot.com/2017/11/inflation-data.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Tuesday Worries](https://verniman.blogspot.com/2017/11/outlook-strong-german-economic-growth.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Tax Plan Advances](https://verniman.blogspot.com/2017/11/tax-bill-advances.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Tax Plan Delay](https://verniman.blogspot.com/2017/11/tax-plan-delay.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Tax Reform Delay](https://verniman.blogspot.com/2017/11/tax-reform-delay.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [The Powell Fed](https://verniman.blogspot.com/2017/11/the-powell-fed.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [Trump on China](https://verniman.blogspot.com/2017/11/trump-on-china.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |
| Unresolved | failed | [US-China deal](https://verniman.blogspot.com/2017/11/us-china-deal.html) | ledger_body_date_mismatch: Ledger date and source Outlook M/D are absent or disagree; no numeric extraction.; session_date_unresolved: Crawl chronology did not resolve a session date; no numeric extraction. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

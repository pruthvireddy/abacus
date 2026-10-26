# Verniman chronological history 10.0.0

Declared interval: 2018-01-01 through 2018-12-31, inclusive. Retained post revisions: 249. Complete: 229; partial: 15; failed numeric extraction: 5. Commentary posts without an explicit daily plan: 0. Distinct stated outlook dates: 245. Extracted numeric level rows: 1937. Calendar dates without observed posts: 120.

Retained-post source coverage: HTML 249/249, Atom 249/249. Image capture coverage: no recorded image capture failures; recorded image failures: 0. Each failure and its source URL/error are retained in issues.csv; complete plan-text extraction does not imply complete image retrieval.

Every in-scope captured revision remains in outlooks and daily_summary.csv, including posts with no safe numeric extraction. Ambiguous branches yield no numeric rows; an independently valid other branch remains. issues.csv records each qualification and raw source branch. coverage.csv logs every calendar date; no_post_observed is a retrieval observation, not proof that a post never existed.

Session dates follow the crawl's chronology, anchored to December 31, 2018, and each body's Outlook M/D. Delivery-contract year is retained separately. Exact one-digit ES contract suffix 8 denotes delivery year 2018 within this independently anchored collection, with the source spelling retained and a single_digit_source_contract warning; no session date is inferred from it. Generic /ES Value headings with no explicit delivery contract retain ES source prices with contract null and source_contract_unspecified warning; explicit present quoting claims may establish a source contract, while ambiguous mentions cause numeric refusal. Explicit today-quoting statements conflicting with the source contract heading cause numeric extraction to be refused, with both branches retained as text. An unqualified future-tense quote naming another contract and justified by present greater volume also causes refusal because operative contract assignment is ambiguous; it is not promoted to a verified today claim. The observed past-tense after-NYSE-bell switch to another contract also causes numeric refusal because the captured body conflicts with its heading. A prospective after-NYSE-bell switch retains the heading contract and a future_intraday_contract_switch warning; it is not treated as an active replacement. The observed present I start quoting another contract as its month increases to equal volume leaves the transition phase ambiguous and causes refusal. These source statements establish neither pre-open availability nor execution timestamps. Conditional future rollover wording remains separate. Duplicate stated dates, metadata date disagreements, source typos and suspicious source prices are retained and flagged. Plural PBTs/GAPs sequences are separate targets, including full point prices joined by and after an explicit plural label; singular two-endpoint ranges are zones. Numbered notes, Reminder/Tips/Basics/Quotes/Notice headings, explicit Rollover week/note/starts, Expiration Week, When VIX climbs above and FOMC reminder paragraph openings terminate plan branches. Explicit postfix support/resistance/magnet labels, Roll-GAP, FOMC Soc/YPOC-FOMC Soc, other supported mixed-case Soc/SoC compounds and HVE-1yrPOC preserve their source wording. The exact mixed-case labels PrevATH and YVAl retain their spelling with explicit warnings. Explicit plural labels can introduce slash-separated full numeric point lists, retaining their notation with a warning; singular or abbreviated slash lists remain unsupported. LIS plus an observed following HVE/YVAH/YVAL/YPOC/YHOD/ATH label sharing one price stays a single compound source label, with a compound_lis_source_label warning. Parenthesized VAR stays a nonnumeric annotation. Standalone SOC: definition paragraphs terminate branches. An otherwise unassigned uppercase source label with no numeric price causes branch refusal. Unlabelled point/zone conjunctions and missing numeric triggers remain unsupported and preserve the affected branch as text with an issue. The nonstandard ONl label retains its exact case and an explicit warning. The exact HVE_PBT label is retained; observed missing whitespace in towardsHVE and a full price immediately followed by HVE is parsed with explicit spelling warnings. A singular zone with an integer anchor and a two-digit decimal suffix retains the anchor's leading digits with an abbreviated_decimal_zone warning; other abbreviated decimal forms remain unsupported.

All available_at values are null: source published/updated claims and current capture times do not establish historical premarket availability. Parsed levels are source observations, not verified trading signals or tested findings. Price outlier warnings use a declared contextual heuristic and never change prices.

Plan A/B/C are source letters, not fixed economic sides. In this release economic side follows the explicit above+buy or below+sell direction/action pair, including exact be/become a buyer/seller and optional try to wording. The separately qualified below+bearish internals+try to lean on one full price+towards labelled-target scenario also maps to bearish without asserting an explicit sell order. Contradictory explicit confirmation wording is refused. The original A/B/C texts are retained in source_plan_a_text/source_plan_b_text/source_plan_c_text, and source_plan_branch on levels plus bullish_source_plan_branch/bearish_source_plan_branch on outlooks/summary preserve the original letter. Duplicate source letters, contradictory or missing directional instructions, and two branches for the same side remain raw with issues; no side is invented from alphabetical position. This release retains the additive source-letter fields and direction-assignment policy introduced in 8.0.0; all earlier releases remain byte-identical.

Source letters reversed relative to A-bullish/B-bearish shorthand: 87 retained posts. This describes source ordering and does not change economic direction or source text.

The source phrases be a buyer, become a buyer, be a seller and become a seller are explicit directional actions, paired with exactly one consistent above/below direction. Source nominal wording remains in both plan text and a source_nominal_action_wording issue. Today's Economic Calendar and subsequent Disclaimer, Questions and Glossary headings terminate plan extraction before calendar numbers. Additional supported source syntax retains compound LIS labels sharing one explicit price or zone, including POC/LVN and the observed hyphenated or spaced HVE/value combinations. Exact RTH Limit Down and RTH limit targets remain qualified source_market_limit_claim observations, without independent exchange-limit or execution validation. An unqualified present I start quoting another contract while the heading names a different contract causes numeric refusal because transition phase is ambiguous. Prospective opening-bell switches, including preposed after the bell and future-tense since NYSE opening bell wording, retain the heading and a future switch warning. The exact mixed-case HVE Tariffs SoC label and parenthesized ETH/ON annotation retain source text and explicit warnings; no source correction or session eligibility is inferred. A single full numeric trigger point without a source label is retained with a null label and unlabelled_trigger_price warning. Bare ranges/lists and unpriced source labels remain unparsed; the opposite branch never supplies a missing label or price.

2018 source attribution adds source_plan_c_text and preserves C as a possible numeric source letter, while neutral A/B/C branches remain verbatim with issues. Literal ESM8/ESU8/ESZ8 codes retain their one-digit spelling; their delivery year is qualified by the separately anchored 2018 chronology. Generic /ES Value bodies with no explicit contract anywhere retain source ES prices with contract null, product ES and source_contract_unspecified. A directly stated present quoting claim can identify an exact delivery contract with source_contract_from_explicit_quoting; ambiguous generic contract mentions remain null and contribute no numeric rows. No delivery contract is inferred from source images, neighboring sessions or price levels. Nullable labels remain limited to exact unlabelled trigger points; nullable delivery contracts are validated only against generic source parents and required warnings.

The source sometimes uses try to buy/sell or be/become a buyer/seller with an ancillary leaning on, above, below or around price/zone before towards. Those execution references stay in source_execution_reference issues and unchanged scenarios rather than replacing the initial conditional threshold or becoming extra targets. Exact quoted Look above/below and fail and Failure to take out/breakdown explanatory tails remain in source_branch_annotation, including their labels/prices/timing, rather than producing extra target rows. A narrowly supported try to lean on clause has no explicit sell order: its source scenario is classified bearish only with one conditional below direction, explicit bearish internals, one full leaning price and a towards labelled-target list, retaining source_lean_on_wording. Leaning zones/lists, contradictory or absent confirmations and ambiguous target prices remain refused. Explicit plural full point lists may use spaces, with space_separated_plural_points; singular or abbreviated space lists remain unsupported. Exact observed Edge/edge/Edge-LIS/Edge-LVN/HGap spellings and ON annotations retain source text and warnings.

Integrity validation covers declared files, schemas, counts, chronology ledger membership and source-plan consistency. It does not establish scientific validity, execution-price correctness or strategy performance. Existing 1.0.0 through 9.0.0 evidence is preserved unchanged.

| Issue code | Count |
|---|---:|
| branch_direction_ambiguous | 6 |
| branch_missing | 3 |
| branch_parse_failed | 18 |
| contract_year_differs_from_session | 10 |
| different_branch_triggers | 67 |
| duplicate_outlook_date | 8 |
| nonstandard_source_label | 12 |
| operative_contract_assignment_ambiguous | 1 |
| operative_contract_header_conflict | 1 |
| other_contracts_mentioned | 8 |
| single_digit_source_contract | 144 |
| singular_multi_point_sequence | 6 |
| source_branch_annotation | 335 |
| source_contract_from_explicit_quoting | 1 |
| source_contract_unspecified | 46 |
| source_execution_reference | 321 |
| source_lean_on_wording | 16 |
| source_level_session_qualifier | 1 |
| source_nominal_action_wording | 369 |
| source_plan_letters_reversed | 87 |
| source_updated_date_differs | 249 |
| source_weekday_differs | 37 |
| space_separated_plural_points | 2 |
| target_opposite_trigger_direction | 8 |
| unlabelled_trigger_price | 53 |

## Collection chronology review

The older-link traversal starts with the retained December 31 seed assigned to 2018 by the prior anchored chronology and corroborating New Year weekday context. The source body does not explicitly print 2018. The seed preserves original source captures and timestamps; newly visited posts receive fresh captures. The older December 29, 2017 boundary stays raw and is excluded from 2018 tables.

All 365 calendar dates remain in coverage. Duplicate source-stated dates and weekday disagreements are retained without correcting dates from prose, event context, publication metadata or update claims. Absences describe observed retrieval coverage rather than proof of no historical post.

Source publication and update claims disagree with body chronology. All 249 in-scope published claims say 2001; 248 update claims say May 30, 2019, and one anomalous rollover post says March 12, 2020. The independently exhausted feed retains every discovered candidate and classification without assigning a session year from metadata alone.

Preserve original Plan A/B/C text and source letters separately from economic side. Require consistent explicit above/buy or below/sell wording, supported buyer/seller instructions, or the bounded below plus bearish-internals lean-on scenario grammar. The latter classifies a bearish source scenario without asserting an explicit sell order: conditional threshold, distinct ancillary lean price and trailing quoted advisory remain unchanged. Neutral, contradictory, duplicated or unresolved assignments retain source text and issues without guessed numeric rows.

An exact single numeric trigger without a source level name retains its price with source_label null and an unlabelled_trigger_price warning. No label is invented. Bare ranges/lists and ambiguous trigger prices remain unsupported. Targets require explicit source labels.

Retain literal single-digit delivery codes such as ESM8 rather than rewriting source notation; any year qualification uses independent anchored chronology. Generic ES Value headings with no resolved delivery contract may retain exact source levels with contract null only under the qualified generic ES policy and source_contract_unspecified warning. No front-month inference is made; ambiguous rollover claims do not receive a guessed delivery contract.

Full-size source images retain exact response bytes, URLs, headers, capture times and hashes. All explicit full-size anchors are reconciled. No chart-only levels are inferred.

Source publication/update claims remain separate from session dates and capture times. Every available_at remains null with historical_availability_unverified; no pre-open timing is inferred. All prior release schemas, producer code and published bytes remain unchanged.

The reviewed older boundary [the 2017-12-29 session](https://verniman.blogspot.com/2017/12/goodbye-2017.html) is retained raw and excluded from the 2018 tables.

The original source captures and traversal ledger remain retained. This publisher consumes the reviewed dates without recomputing years from source updates or delivery contracts. In this 2018 collection, source-claimed updates may be from later years; metadata years do not reassign retained body dates.

## Weekdays without a captured dated post (16)

2018-01-01, 2018-01-15, 2018-01-31, 2018-02-15, 2018-02-19, 2018-03-15, 2018-03-30, 2018-05-25, 2018-05-28, 2018-07-04, 2018-08-02, 2018-08-17, 2018-09-03, 2018-11-22, 2018-12-05, 2018-12-25

These are observed calendar gaps. No holiday or exchange-session eligibility is inferred, and a gap is not proof that a post never existed.

| Missing weekday | Nearest earlier captured date | Nearest later captured date |
|---|---|---|
| 2018-01-01 | No captured dated post in this interval | 2018-01-02: [Welcome 2018](https://verniman.blogspot.com/2018/01/welcome-2018.html) |
| 2018-01-15 | 2018-01-12: [Bank Earnings](https://verniman.blogspot.com/2018/01/bank-earnings.html) | 2018-01-16: [Finally 2800!](https://verniman.blogspot.com/2018/01/finally-2800.html) |
| 2018-01-31 | 2018-01-30: [Last Yellen's FOMC](https://verniman.blogspot.com/2018/01/last-yellens-fomc.html); [Red Tuesday](https://verniman.blogspot.com/2018/01/red-tuesday.html) | 2018-02-01: [Big Tech Earnings](https://verniman.blogspot.com/2018/02/big-tech-earnings.html) |
| 2018-02-15 | 2018-02-14: [Inflation Data](https://verniman.blogspot.com/2018/02/inflation-data.html); [Inflation is OK](https://verniman.blogspot.com/2018/02/inflation-is-ok.html) | 2018-02-16: [Major Recovery](https://verniman.blogspot.com/2018/02/major-recovery.html) |
| 2018-02-19 | 2018-02-16: [Major Recovery](https://verniman.blogspot.com/2018/02/major-recovery.html) | 2018-02-20: [Doubts Return](https://verniman.blogspot.com/2018/02/doubts-return.html) |
| 2018-03-15 | 2018-03-14: [Retail Sales](https://verniman.blogspot.com/2018/03/retail-sales.html) | 2018-03-16: [Witching Day](https://verniman.blogspot.com/2018/03/witching-day.html) |
| 2018-03-30 | 2018-03-29: [Bye Bye Q1](https://verniman.blogspot.com/2018/03/bye-1st-q1.html) | 2018-04-02: [China Hits Back](https://verniman.blogspot.com/2018/04/china-hits-back.html) |
| 2018-05-25 | 2018-05-24: [After FED Minutes](https://verniman.blogspot.com/2018/05/after-fed-minutes.html); [US-NK Setback](https://verniman.blogspot.com/2018/05/us-nk-setback.html) | 2018-05-29: [Italian Crisis](https://verniman.blogspot.com/2018/05/italian-crisis.html) |
| 2018-05-28 | 2018-05-24: [After FED Minutes](https://verniman.blogspot.com/2018/05/after-fed-minutes.html); [US-NK Setback](https://verniman.blogspot.com/2018/05/us-nk-setback.html) | 2018-05-29: [Italian Crisis](https://verniman.blogspot.com/2018/05/italian-crisis.html) |
| 2018-07-04 | 2018-07-03: [Shortened Day](https://verniman.blogspot.com/2018/07/shortened-day.html) | 2018-07-05: [FOMC Minutes](https://verniman.blogspot.com/2018/07/fomc-minutes.html) |
| 2018-08-02 | 2018-08-01: [FOMC Day](https://verniman.blogspot.com/2018/08/fomc-day.html) | 2018-08-03: [Jobs Report](https://verniman.blogspot.com/2018/08/trade-war-fears.html) |
| 2018-08-17 | 2018-08-16: [Back To The Table](https://verniman.blogspot.com/2018/08/back-to-table.html); [Consumer Sentiment](https://verniman.blogspot.com/2018/08/trump-qes.html) | 2018-08-20: [Jackson Hole Week](https://verniman.blogspot.com/2018/08/jackson-hole-week.html) |
| 2018-09-03 | 2018-08-31: [Consumer data](https://verniman.blogspot.com/2018/08/consumer-data.html) | 2018-09-04: [Short Week](https://verniman.blogspot.com/2018/09/short-week.html) |
| 2018-11-22 | 2018-11-21: [Some Respite](https://verniman.blogspot.com/2018/11/some-respite.html) | 2018-11-23: [Black Friday](https://verniman.blogspot.com/2018/11/black-friday.html) |
| 2018-12-05 | 2018-12-04: [Skepticism](https://verniman.blogspot.com/2018/12/outlook-1204-rapprochement-between.html) | 2018-12-06: [Truce in doubt](https://verniman.blogspot.com/2018/12/truce-in-doubt.html) |
| 2018-12-25 | 2018-12-24: [Christmas Eve](https://verniman.blogspot.com/2018/12/outlook-1224-following-worst-week-for.html) | 2018-12-26: [After Christmas](https://verniman.blogspot.com/2018/12/after-christmas.html) |

Neighbor links identify the closest captured stated dates for review; they are not source posts for an absent date or proof of a historical absence. A retained post with refused numeric extraction still counts as a captured date.

## Weekend stated dates (0 posts)

None.

## Duplicate stated dates (4 groups)

| Stated date | Source posts |
|---|---|
| 2018-01-30 | [Last Yellen's FOMC](https://verniman.blogspot.com/2018/01/last-yellens-fomc.html); [Red Tuesday](https://verniman.blogspot.com/2018/01/red-tuesday.html) |
| 2018-02-14 | [Inflation Data](https://verniman.blogspot.com/2018/02/inflation-data.html); [Inflation is OK](https://verniman.blogspot.com/2018/02/inflation-is-ok.html) |
| 2018-05-24 | [After FED Minutes](https://verniman.blogspot.com/2018/05/after-fed-minutes.html); [US-NK Setback](https://verniman.blogspot.com/2018/05/us-nk-setback.html) |
| 2018-08-16 | [Back To The Table](https://verniman.blogspot.com/2018/08/back-to-table.html); [Consumer Sentiment](https://verniman.blogspot.com/2018/08/trump-qes.html) |

Each post revision retains its original stated date. No duplicate was silently reassigned or removed.

## Partial or failed numeric extraction (20 posts)

| Stated date | Status | Source | Errors retained |
|---|---|---|---|
| 2018-01-04 | partial | [Watching Excess](https://verniman.blogspot.com/2018/01/watching-excess.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2725-2732 |
| 2018-01-05 | partial | [NFP & Excess](https://verniman.blogspot.com/2018/01/nfp-excess.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2740-2743 |
| 2018-01-08 | partial | [Earnings Season](https://verniman.blogspot.com/2018/01/earnings-season.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2753 |
| 2018-01-09 | failed | [Market Euphoria](https://verniman.blogspot.com/2018/01/market-euphoria.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONL and YVAL-LVN 2741-40; branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2753-2757 |
| 2018-01-10 | partial | [China Report](https://verniman.blogspot.com/2018/01/china-report.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONL and LVN 2735 GBT 2732 |
| 2018-01-11 | failed | [Just Fake News](https://verniman.blogspot.com/2018/01/just-fake-news.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONL and LVN-YVAL 2744; branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2758-59 |
| 2018-01-12 | failed | [Bank Earnings](https://verniman.blogspot.com/2018/01/bank-earnings.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2780-83; branch_parse_failed: source label has no assigned explicit numeric level: ONL and LVN 2760 |
| 2018-01-16 | partial | [Finally 2800!](https://verniman.blogspot.com/2018/01/finally-2800.html) | branch_parse_failed: ambiguous abbreviated decimal endpoint |
| 2018-01-17 | partial | [Fed-Filled Day](https://verniman.blogspot.com/2018/01/fed-filled-day.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and YVAH-LVN 2798 PBT 2805 |
| 2018-01-24 | partial | [More Records High ](https://verniman.blogspot.com/2018/01/new-record-high_24.html) | branch_parse_failed: source label has no assigned explicit numeric level: GAP 2839.50 and ONL |
| 2018-03-09 | failed | [Jobs Report](https://verniman.blogspot.com/2018/03/jobs-report.html) | operative_contract_assignment_ambiguous: A generic /ES Value heading and other contract mentions do not uniquely establish an operative contract. No first-token or front-month assignment is made; numeric extraction is refused. |
| 2018-04-17 | partial | [More Earnings](https://verniman.blogspot.com/2018/04/more-earnings.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONH and PBTs 2700-2708 |
| 2018-05-17 | partial | [Yields Keep Climbing](https://verniman.blogspot.com/2018/05/yields-keep-climbing.html) | branch_parse_failed: space-separated point lists require an explicit plural source label: PBT 2733 2741 |
| 2018-07-06 | partial | [NFP / Trade War](https://verniman.blogspot.com/2018/07/nfp-trade-war.html) | branch_parse_failed: source label has no assigned explicit numeric level: YVAH |
| 2018-08-21 | partial | [Bull Market](https://verniman.blogspot.com/2018/08/bull-market.html) | branch_direction_ambiguous: Source Plan B: lean-on classification requires explicit below/bearish internals and one full leaning price before towards; retain source text without a numeric side assignment.; branch_missing: No unique labelled plan branch was found. |
| 2018-09-05 | partial | [Weak Opening](https://verniman.blogspot.com/2018/09/weak-opening.html) | branch_direction_ambiguous: Source Plan A: lean-on classification requires explicit below/bearish internals and one full leaning price before towards; retain source text without a numeric side assignment.; branch_missing: No unique labelled plan branch was found. |
| 2018-09-13 | partial | [CPI pressure](https://verniman.blogspot.com/2018/09/cpi-pressure.html) | branch_parse_failed: source label has no assigned explicit numeric level: YHOD |
| 2018-10-01 | partial | [NAFTA deal](https://verniman.blogspot.com/2001/10/nafta-deal.html) | branch_direction_ambiguous: Source Plan A: source branch lacks exactly one explicit above/below direction; retain source text without a numeric side assignment.; branch_missing: No unique labelled plan branch was found. |
| 2018-11-20 | partial | [Tech Weakness](https://verniman.blogspot.com/2018/11/tech-weakness_20.html) | branch_parse_failed: source label has no assigned explicit numeric level: ONL and HVEs 2652-2646-2627-2620. |
| 2018-12-13 | failed | [Rollover Days](https://verniman.blogspot.com/2018/12/rollover-day.html) | operative_contract_header_conflict: The source explicitly states it is currently quoting another contract, contradicting its contract heading; both branch texts and the heading are retained but numeric extraction is refused. |

Original branch text and capture locators remain in outlooks, including every branch that yielded no numeric rows.

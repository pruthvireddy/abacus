# Phase 6 prospective calendar

The fixed nominal sample contains **20 full, supported RTH sessions**, beginning
**November 2** and ending **December 8, 2026**. None has been observed or captured
in Phase 6A. [calendar.json](calendar.json) is the machine-readable calendar;
the actual protocol-freeze receipt binds its exact bytes and actual UTC time.
This calendar is valid only if that freeze occurs before November 2's 09:25
New York cutoff. A later freeze requires a new declared calendar before any
observation, rather than relabeling a missed first date.

| Scheduled week | Fixed session dates |
|---|---|
| November 2 | November 2, 3, 4, 5, 6 |
| November 9 | November 9, 10, 11, 12, 13 |
| November 16 | November 16, 17, 18, 19, 20 |
| November 23 | November 23, 24, 25 |
| December 7 | December 7, 8 |

Every scheduled date remains in the final report. Unexpected closure, missing
inputs, absence of sources, late capture, exposure or capture failure retains
its actual status. No extension or replacement is allowed after freeze.

## Calendar sources and conservative support rule

The official [NYSE 2026 calendar](https://www.nyse.com/markets/hours-calendars)
lists Thanksgiving, November 26, as closed, and November 27 as an early cash
close at 13:00 Eastern. Its ordinary core session is 09:30–16:00 Eastern.
November 11 is not a listed cash-market holiday. The
[CME 2026 Globex holiday list](https://www.cmegroup.com/trading-hours.html)
identifies the Thanksgiving holiday period; Veterans Day appears elsewhere in
clearing/settlement information and must not be mistaken for an ES Globex
closure.

The study adopts a **conservative nominal eligibility policy**: current cash
RTH must be full, and the frozen mechanism's required history must be free of
known closed/shortened cash sessions. This is a pre-prediction calendar rule,
not an observation that particular future ES bars are missing. It does not
change a detector, profile window or strict expected-weekday member.

| Predeclared exclusion | Reason and inherited support |
|---|---|
| November 26 | Closed cash RTH; excluded current session |
| November 27 | Shortened cash RTH; preceding closed day also affects prior/full RTH, composite and current-week inputs |
| November 30 | Previous week's holiday and shortened day; strict prior weekday and three-RTH composite also affected |
| December 1–2 | Previous week affected; strict three-weekday composite still includes a non-full session |
| December 3–4 | Previous completed week still contains the holiday/shortened session |

The [unchanged Phase 3 composite](../phase3/calculation-specification.md)
requires three expected 09:30–16:00 RTH weekdays without holiday substitution.
The [Phase 5 coverage gate](../phase5/audit_development.py) also checks fixed
prior-full, prior-RTH, overnight, current-week and previous-week clocks. The
calendar module reproduces those eight window boundaries. Applying the
conservative policy returns December 7 as the first subsequent supported date;
the two remaining sample sessions are therefore December 7 and 8. The
machine record retains every affected window, not only these summaries.

The public CME page's dynamic, product-specific Thanksgiving close table was
not captured. The [CME November 27 settlement notice](https://www.cmegroup.com/tools-information/holiday-calendar/files/2026/thanksgiving-holiday-settlement-times-2026.pdf)
states an equity settlement time, which is **not used as a futures trading
close**. NYSE cash close is also not presented as ES Globex close. This limit
does not create a holiday substitution: all affected dates/windows are already
excluded by the stricter declared calendar policy. Each scheduled date must
still pass actual OHLCV coverage and identity checks; nominal eligibility does
not establish future data access or completeness.

## Dated contract and daylight saving

Retain **CME_MINI:ESZ2026**, individual unadjusted December contract, CME GLOBEX;
no continuous series or automatic roll. CME's
[U.S. equity index roll calendar](https://www.cmegroup.com/trading/equity-index/rolldates.html)
lists December 18 expiry and December 14 customary roll for December 2026.
[Rule 358](https://www.cmegroup.com/rulebook/CME/IV/350/358/358.pdf) places final
settlement on the third Friday and ends expiring trading at normal NYSE opening.
All scheduled closes occur before both dates. The validator conservatively
rejects a block extending into the announced roll date; it does not claim a
particular future volume-roll instant or guarantee future liquidity.

[NIST's 2026 DST rule](https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst)
ends daylight time on November 1 at 02:00 local, repeating the 01:00 hour.
Use `America/New_York`, never a permanently fixed UTC offset. Every scheduled
09:25 cutoff in this block is **14:25 UTC / 09:25 EST**. The terminal five-minute
bar remains 09:20–09:25 New York. The first nominal prior-week input begins
October 25 at 18:00 EDT; independent warm-up market data is distinct from the
previously exposed source-answer record and does not authorize reopening it.

## Retained version and validator

Calendar version: `study29-phase6-nominal-20261031-v1`, researched October 31 UTC.
The stage's `calendar-evidence/source-manifest.json` pins the official URLs,
year/sections, facts and exact retained web-tool retrieval. Its SHA-256 binds
that retrieval output, **not raw remote HTML/PDF bytes or independent time
certification**. Direct raw-page download attempts failed DNS/read timeout and
did not produce a remote-file hash. No Verniman source answers were inspected.

Run the read-only validator with the actual timestamp from the preparation
freeze, not a future date invented to pass it:

```sh
./scripts/uv run --locked --no-sync python studies/29_verniman_level_reconstruction/phase6/calendar_control.py --calendar studies/29_verniman_level_reconstruction/phase6/calendar.json --frozen-at ACTUAL_PROTOCOL_FREEZE_ISO_TIMESTAMP
```

This checks dates, exclusions, strict window membership, New York conversions
and the fixed dated-contract interval. It does not execute Pine, fetch market
data, verify future observations or complete Phase 6.

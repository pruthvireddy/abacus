# Forex News

`forex_news.pine` merges the current Pine v6 version of the toodegrees Live Economic Calendar with the useful alert/deduplication ideas from the Nachodog fork.

The indicator keeps the full six-field calendar table—day, date, time, currency, expected impact, and event name—while letting chart shading use a narrower, independent event selection.

## Default behavior

- Shades FOMC/rate decisions, CPI, and NFP-related releases.
- Uses a centered one-hour window: 30 minutes before and 30 minutes after the scheduled release.
- Draws a compact, impact-colored circle at each shaded release. Hovering it shows the exact event details and DXY importance rank; simultaneous releases share one numbered marker.
- Shows high- and medium-impact events in the weekly table.
- Keeps table contents independent from the shaded-event filters.
- Makes event lines and labels follow the shaded-event filters.

## Event selection

The settings sort built-in categories by their typical immediate USD/DXY impact:

1. FOMC and central-bank decisions — Extreme
2. NFP and the Employment Situation — Very high
3. CPI — Very high
4. Retail sales — High
5. Advance GDP — Medium-high
6. ISM / PMI — Medium-high
7. ADP / jobless claims / JOLTS — Medium
8. PPI — Medium-low
9. PCE — Medium-low
10. Central-bank speeches — Variable
11. Other filtered events — Variable

Custom comma-separated event-title keywords remain available for releases outside these categories.

Filters are matched against the event titles supplied by the Forex Factory feed. If the upstream feed renames an event, add a distinctive part of its new title to **Custom title keywords**.

## Important limitations

- The upstream Pine Seeds calendar is maintained by toodegrees and refreshed on their schedule. Confirm critical releases against an official calendar.
- The feed includes scheduled metadata, not Actual, Forecast, or Previous values.
- Background shading snaps to chart bars. Five- and fifteen-minute time-based charts represent a one-hour window most precisely.
- Hover circles appear once a chart bar reaches the scheduled release. Upcoming details remain available in the table and event line until then.
- All Day and Tentative events are excluded from timed shading by default.
- The script supports 30-second through Daily charts.
- Fixed UTC offsets do not automatically adjust for daylight saving time.

## Attribution and license

This derivative retains the Mozilla Public License 2.0 notice and credits the original toodegrees calendar and Nachodog fork. If published publicly on TradingView, keep the source open, preserve attribution, and follow TradingView's open-source reuse rules.

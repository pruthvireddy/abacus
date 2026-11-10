# Daily Facts volume pilot decisions

- The [frozen Bhishma request](../../requests/inbox/daily_market_facts__1.0.0.yaml)
  fixes the audited period, all six windows and the retained sources.
- The volume comparison pairs the hours within each asset and session. A complete
  Globex session is unnecessary for these two RTH windows.
- GC uses its own 08:20–13:30 New York RTH interval. Each asset's denominators and
  exclusions are displayed alongside the descriptive estimates.

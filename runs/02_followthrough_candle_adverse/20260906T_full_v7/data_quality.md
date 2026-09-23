# Data quality

All seven available files were read without changing `data/`. Each is headerless and semicolon-delimited with five fields interpreted as timestamp/open/high/low/close. The `%Y-%d-%m %H:%M:%S` format parses every row. All OHLC rows satisfy their inequalities and all prices align to the configured exchange ticks.

- ES R4 `ESU6_rangexv4_0614_0904.csv`: 52,591 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 4,608 rows in repeated timestamps, 6 dojis.
- ES R5 `ESU6_rangexv5_0614_0904.csv`: 36,188 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 2,702 rows in repeated timestamps, 8 dojis.
- ES R6 `ESU6_rangexv6_0614_0904.csv`: 26,248 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 1,713 rows in repeated timestamps, 5 dojis.
- GC R6 `GCZ6_rangexv6_0614_0904.csv`: 152,418 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 26,909 rows in repeated timestamps, 4 dojis.
- GC R10 `GCZ6_rangexv10_0614_0904.csv`: 67,164 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 7,330 rows in repeated timestamps, 2 dojis.
- NQ R10 `NQU6_rangexv10_0614_0904.csv`: 417,815 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 126,122 rows in repeated timestamps, 5 dojis.
- NQ R20 `NQU6_rangexv20_0614_0904.csv`: 125,793 rows, 0 timestamp parse failures, 0 OHLC failures, 0 off-tick rows, 0 timestamp regressions, 15,893 rows in repeated timestamps, 3 dojis.

Repeated timestamps are preserved in original row order. They do not affect this bar-sequence study. The final row of each file is excluded because completion cannot be verified. Provisional export-calendar dates prevent reversals and follow-through pairs from crossing a date boundary.

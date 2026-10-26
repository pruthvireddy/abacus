# NQ advanced AMD video study

Study 17 explains [Tmac's advanced AMD lesson](https://www.youtube.com/watch?v=mmem9CI7vvw)
through its full English caption track and fourteen inspected chart screenshots.
The central idea is to carry a conditional higher-timeframe directional view into
intraday execution, then require suitable local structure before entering.

**Evidence status:** completed qualitative source review of one selected week.
No backtest, independently verified trading record, or demonstrated profitable
strategy. The quarterly-candle claim remains unverified, and the video explicitly
leaves its all-time-high objective unmet during the reviewed week.

## Read the study

- [Illustrated offline report](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.html)
- [Detailed Markdown report](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/report.md)
- [Timestamped chart atlas](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/charts.csv)
- [Claim and evidence ledger](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/claims.csv)
- [Complete timeline coverage](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/tables/coverage.csv)
- [Evidence manifest](../../runs/17_nq_advanced_amd_video/20261005T172713Z_video17/manifest.json)

## Protocol and reproduction

[Plan](plan.md), [settings](study.yaml), [source lock](inputs.lock.json), and
[decisions](notes.md) define the review. Screenshots are actual paused YouTube
frames, cropped to the player; original chart drawings were preserved.
The caption input is retained in ignored research storage with a checksum and
portable locator in the source lock. It needs a separate backup.

The source-specific `run.py` packages authored observations and source captures;
it does not calculate market statistics or download arbitrary videos. To check
the saved bundle without changing it:

```sh
python3 studies/17_nq_advanced_amd_video/run.py verify --bundle runs/17_nq_advanced_amd_video/20261005T172713Z_video17
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py --check
```

Reproduction and acquisition details are frozen in the run's `provenance/`
directory. New interpretations or empirical tests require a new run. No Narada
publication or strategy card was created from this source-only evidence.

# Exact commands and research operations

The source review used the existing workspace and its locked environment; no dependency sync or market-data run was performed. The following public page captures were executed as individual curl invocations.

```sh
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2009/09/fed-decision.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T01.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/04/glossary-of-terms.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T02.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/07/using-market-delta.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T03.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/09/squawk-box-audio.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T04.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/03/trading-fomc.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T05.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2015/05/closing-0514.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T06.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/09/trading-execution_8.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T07.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/07/trade-market-value.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T08.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2015/05/opening-0518.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T09.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2012/06/bookmap-basic.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T10.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2011/07/heatmap-levels.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T11.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/01/trade-without-charts.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T12.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/08/scalping-dom.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T13.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/08/scalping-tape.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T14.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/04/the-profile-traders_26.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T15.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/03/trading-vpoc-shifts.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T16.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2012/01/market-profile.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T17.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2013/03/trade-market-value.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T18.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2019/06/dalton-unplugged.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T19.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/02/the-bandwagon-theory.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T20.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2017/01/markets-correlation.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T21.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/04/opening-update-0408.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T22.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2010/05/release-ego.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T23.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2010/06/motivational-video.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T24.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2010/04/missing-trades.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T25.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2011/07/institutional-traders.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T26.html'
curl -L --fail --max-time 25 'https://verniman.blogspot.com/2014/03/futures-rollover.html' -o 'work/27_verniman_method_knowledge/20261023T174000Z_review27/source-captures/T27.html'
```

Original linked image URLs and destination paths are in image-inventory.json; each retained image used the same curl flags. Source articles were extracted from post-body HTML with the standard-library HTML parser; the full HTML and exact derived bytes are separately pinned. The original HTTP redirect chain was not captured.

The in-app browser opened each video watch URL from media-inventory.json and called its documented `content.exportYouTubeTranscript()` API. Some pages needed their heading to finish loading and the visible transcript panel opened before export. Early no-transcript results were superseded where later exports succeeded. Browser export files were copied byte-for-byte from its temporary export directory to the retained stage. The four final access gaps and one quality gap remain explicit. Full video play-through, audio transcription and independent frame inspection were not performed.

Verification commands actually executed:

```sh
python3 scripts/check-agent-docs.py
./scripts/check-workspace --profile metadata
python3 -m unittest discover -s scripts/tests -p 'test_check_registry.py'
python3 work/27_verniman_method_knowledge/20261023T174000Z_review27/audit_review.py work/27_verniman_method_knowledge/20261023T174000Z_review27
./scripts/check-workspace --report work/27_verniman_method_knowledge/20261023T174000Z_review27/checks/workspace-default.json
```

The first compatibility-gate attempt failed on sandbox access to uv cache; the approved retry used the existing locked environment without sync. That retry passed documentation and failed Bhishma because retained data prerequisites were missing. Its actual report preserves failure and fail-fast unexecuted checks. This review does not claim that gate passed.

The exact initial interactive extraction/snippet-reading tool history is not embedded as a full terminal transcript. Captures, authored observations, byte identities, review coverage declarations and the read-only audit program are retained; this is a qualitative source-review provenance record, not a claim of an entirely automated semantic research pipeline.

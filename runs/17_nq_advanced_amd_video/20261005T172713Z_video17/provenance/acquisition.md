# Acquisition and reproduction

The user supplied the YouTube URL. Source review used the full automatic English
caption export and fourteen inspected player frames. The full video was not
saved. No source trading figures were recalculated.

## Source access

The web text reader returned a cache miss. YouTube oEmbed returned the video title
and Tmac channel identity. The connected Chrome browser displayed the title,
27:11 duration, and an expanded description showing October 5, 2026. Only relevant
source metadata was retained; recommendations, account details and comments were
excluded. The browser's content.exportYouTubeTranscript() exported the UTF-8
English automatic captions. The source lock pins the retained copy.

The browser opened the supplied URL, paused playback, and sought using the player
seek slider in five-second steps. After seeking, the page was scrolled to the top
and a settled paused frame was captured with:

```javascript
const media = await tab.playwright.locator('#movie_player').evaluate(el => {
  const v = el.querySelector('video');
  return {currentTime:v.currentTime,duration:v.duration,paused:v.paused,readyState:v.readyState};
});
const bytes = await tab.screenshot({clip:{x:14.4,y:61.2,width:1196.55,height:673.05}});
```

The browser capture scale produced 1329 by 748 pixel JPEG player excerpts.
Early captures used settled displayed player times; captures 06–14 additionally
record the paused media time in capture-log.json. Seeking can leave the ARIA
label temporarily stale. Frame 06 was recaptured at 923.829009 seconds using the
media check. Original chart annotations and facecam remain; there are no generated
charts, reconstructed candles, or synthetic fills. Image selection was purposive.

## Local commands

Commands run from the Abacus workspace root. The publication root of `.` was
read from config/paths.local.toml before source retention and supplied explicitly.
The authoring script is preserved as provenance/source-authoring.py. It creates
tables and metadata from the inspected source and copies the caption input into
retained research storage. Its temporary input path is historical acquisition
provenance; later verification uses the portable path in inputs.lock.json.

```sh
python3 work/17_nq_advanced_amd_video/prepare.py
python3 studies/17_nq_advanced_amd_video/run.py assemble --source work/17_nq_advanced_amd_video --bundle work/17_nq_advanced_amd_video/20261005T172713Z_video17 --publication-root .
python3 studies/17_nq_advanced_amd_video/run.py verify --bundle runs/17_nq_advanced_amd_video/20261005T172713Z_video17 --publication-root .
python3 scripts/check-agent-docs.py
python3 scripts/build-research-index.py
python3 scripts/build-research-index.py --check
```

The exact sealing command is recorded in manifest.json. The report is rendered
from authored Markdown and saved image/table evidence using the snapshot of the
study-specific standard-library packager. A later re-render must go to a new
presentation revision, not overwrite this completed run. The run's code snapshot
preserves dirty/untracked study source; the Git status is context for unrelated
pre-existing workspace changes, not a claim to snapshot the entire repository.

## Review scope

All caption intervals are assigned a review note in tables/coverage.csv, from
0 through the media duration. Screenshot inspection covers the selected visual
examples, not every frame of the 27-minute video. The evidence does not include
independent listening verification of every auto-caption, the original private
messages, an account statement, tick history, or an independently reconstructed
news release. Ambiguous jargon remains unresolved.

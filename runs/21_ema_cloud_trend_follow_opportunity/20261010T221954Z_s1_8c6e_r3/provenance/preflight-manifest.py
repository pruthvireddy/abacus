"""Build an explicit preliminary evidence inventory without sealing."""
from pathlib import Path
import json, sys
stage = Path(__file__).resolve().parents[1]
root = stage.parents[2]
sys.path.insert(0, str(root / 'studies/21_ema_cloud_trend_follow_opportunity'))
from src.execution import assert_frozen_sources
from src.pipeline import build_manifest
assert_frozen_sources(stage, root)
(stage / 'manifest.json').write_text(json.dumps(build_manifest(stage), indent=2) + '\n')
print('Preliminary explicit evidence inventory built; scientific receipts remain separate')

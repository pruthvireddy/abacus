"""Study-owned identities and the existing saved-JSON convention."""

import json
from pathlib import Path


DATASET_ID = "nq_causal_vp_hvn__1.0.0"
MINUTE = 60_000_000_000
PACKAGE_SOURCE_PATHS = (
    "packages/bhishma/src/abacus_bhishma/paths.py",
    "packages/bhishma/src/abacus_bhishma/provenance.py",
    "packages/bhishma/src/abacus_bhishma/publication_safety.py",
)


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

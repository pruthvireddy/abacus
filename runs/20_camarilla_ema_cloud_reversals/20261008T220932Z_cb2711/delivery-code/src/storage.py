import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value

def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n")

def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def save_csv(path, frame):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format="%.10g", na_rep="")

def guard(work):
    if (Path(work) / "SEALED").exists():
        raise RuntimeError("Execution staging has been sealed; choose a new run ID")

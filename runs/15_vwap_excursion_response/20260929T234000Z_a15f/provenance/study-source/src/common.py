"""Study-local identities, serialization, session clock, and artifact helpers."""
from __future__ import annotations
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

STUDY = '15_vwap_excursion_response'
OWNER = Path(__file__).resolve().parents[1]
SESSIONS = {'asia': ('20:00', '03:00', -1), 'london': ('03:00', '09:00', 0),
            'ny': ('09:30', '16:00', 0), 'globex': ('18:00', '17:00', -1)}
HORIZONS = (5, 10, 15, 20, 50)
THRESHOLDS = (2., 2.5, 3.)
PRODUCTS = ('ES', 'NQ', 'GC')
MINUTE = 60_000_000_000
SCHEMA_VERSION = '1.0.0'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def utcnow(): return datetime.now(timezone.utc).isoformat()

def dump(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    def default(x):
        if isinstance(x, (datetime, date, pd.Timestamp)): return x.isoformat()
        if isinstance(x, Path): return str(x)
        if isinstance(x, np.generic): return x.item()
        if isinstance(x, np.ndarray): return x.tolist()
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(obj, indent=2, default=default, allow_nan=False) + '\n')

def window(day, session):
    day = date.fromisoformat(str(day)[:10])
    start, end, offset = SESSIONS[session]
    a = pd.Timestamp(f'{day + timedelta(days=offset)} {start}', tz='America/New_York')
    b = pd.Timestamp(f'{day} {end}', tz='America/New_York')
    return a.tz_convert('UTC'), b.tz_convert('UTC')

def stamp(ns): return pd.Timestamp(int(ns), tz='UTC').isoformat()

def week(day):
    y,w,_ = date.fromisoformat(str(day)[:10]).isocalendar()
    return f'{y}-W{w:02d}'

def age_bin(x): return '00-09' if x < 10 else '10-29' if x < 30 else '30-59' if x < 60 else '60+'

def latency_bin(x):
    return '01-05' if x<=5 else '06-10' if x<=10 else '11-15' if x<=15 else '16-20' if x<=20 else '21-50' if x<=50 else '>50'

def save_table(path, rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path.with_suffix('.parquet'), index=False)
    frame.to_csv(path.with_suffix('.csv'), index=False)
    return frame

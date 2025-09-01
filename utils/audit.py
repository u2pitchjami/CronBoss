# utils/audit.py
from __future__ import annotations

import json
from pathlib import Path
import time
from typing import TypedDict


class RunRecord(TypedDict, total=False):
    ts: float
    script: str
    status: str
    duration: float
    returncode: int | None
    source_file: str
    stdout_tail: str | None
    stderr_tail: str | None


def append_run_record(path: str | Path, rec: RunRecord) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec.setdefault("ts", time.time())
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

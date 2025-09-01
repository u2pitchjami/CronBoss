from __future__ import annotations

import fcntl
import hashlib
import os
from pathlib import Path
from typing import IO

from utils.config import LOCK_ROOT


def _lock_path_for_script(script_path: str | os.PathLike[str]) -> Path:
    p = Path(script_path)
    digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
    return Path(LOCK_ROOT) / f"{digest}.lock"


def try_acquire_task_lock(script_path: str | os.PathLike[str]) -> IO[str] | None:
    path = _lock_path_for_script(script_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = path.open("w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fh.write(str(os.getpid()))
        fh.flush()
        return fh
    except BlockingIOError:
        try:
            fh.close()
        except Exception:
            pass
        return None


def release_task_lock(fh: IO[str] | None) -> None:
    if fh is None:
        return
    try:
        fcntl.flock(fh, fcntl.LOCK_UN)
    finally:
        try:
            fh.close()
        except Exception:
            pass

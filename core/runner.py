#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import shlex
import subprocess
import sys

from utils.logger import get_logger
from utils.types import RunHandle

logger = get_logger("CronBoss")


def run_python_script(
    script_path: str | Path,
    cwd: str | Path,
    args: str = "",
    interpreter: str | None = None,
) -> RunHandle:
    """
    Lance un script Python et retourne un handle de suivi (proc + cmd + script).

    :param script_path: chemin du script .py
    :param cwd: répertoire de travail (sera passé à Popen)
    :param args: arguments CLI (string, sera parsé via shlex.split)
    :param interpreter: chemin d'interpréteur Python (venv) sinon sys.executable
    :return: RunHandle (TypedDict) contenant au minimum 'proc'
    """
    try:
        full_path = Path(script_path).resolve()
        workdir = Path(cwd).resolve()

        # Construire l'env proprement
        env: Mapping[str, str] = os.environ.copy()
        # logger.debug(f"env: {env}")
        logger.debug("⏰ [Python] %s cmd=%s cwd=%s", full_path, args, workdir)
        current_pp = env.get("PYTHONPATH", "")
        env = {
            **env,
            "PYTHONPATH": f"{workdir}{os.pathsep}{current_pp}" if current_pp else str(workdir),
        }
        cmd: list[str] = [interpreter or sys.executable, str(full_path), *shlex.split(args)]
        logger.info("⏰ [Python] %s cmd=%s cwd=%s", full_path, cmd, workdir)

        proc: subprocess.Popen[str] = subprocess.Popen(
            cmd,
            env=env,  # Mapping[str, str] accepté à l'exécution
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
        )
        return {"proc": proc, "cmd": cmd, "script": str(full_path)}
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("🚨 Erreur Python pour %s : %s", script_path, exc)
        raise


def run_bash_script(
    script_path: str | Path,
    cwd: str | Path,
    args: str = "",
) -> RunHandle:
    """
    Lance un script Bash et retourne un handle de suivi (proc + cmd + script).

    :param script_path: chemin du script .sh
    :param cwd: répertoire de travail
    :param args: arguments CLI (string, sera parsé via shlex.split)
    """
    try:
        full_path = Path(script_path).resolve()
        workdir = Path(cwd).resolve()
        cmd: list[str] = ["bash", str(full_path), *shlex.split(args)]

        logger.info("⏰ [Bash] %s cmd=%s cwd=%s", full_path, cmd, workdir)

        proc: subprocess.Popen[str] = subprocess.Popen(
            cmd,
            cwd=str(workdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            close_fds=True,
        )
        return {"proc": proc, "cmd": cmd, "script": str(full_path)}
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("🚨 Erreur Bash %s : %s", script_path, exc)
        raise

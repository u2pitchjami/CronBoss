#!/usr/bin/env python3
import subprocess
import sys
import os
import shlex
from pathlib import Path
from utils.logger import get_logger
from utils.config import SCRIPT_DIR

logger = get_logger("CronHub")

def run_python_script(script_path, args="", interpreter=None):
    """Lance un script Python et retourne un handle de suivi."""
    try:
        full_path = Path(script_path)
        cwd = Path(full_path).parent

        # Détection projet → sert à ajuster PYTHONPATH
        project_root = None
        for parent in Path(full_path).parents:
            if parent.name == "brain_ops":
                project_root = parent
                break
        if not project_root:
            project_root = Path(full_path).parent.parent
    
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"

        cmd = [interpreter or sys.executable, str(full_path)] + shlex.split(args)
        logger.info(f"⏰ [Python] {full_path} cmd={cmd} cwd={cwd}")

        proc = subprocess.Popen(
            cmd,
            env=env,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {"proc": proc, "cmd": cmd, "script": str(full_path)}
    except Exception as e:
        logger.error(f"🚨 Erreur Python {e}")
        raise


def run_bash_script(script_path, args=""):
    """Lance un script Bash et retourne un handle de suivi."""
    try:
        full_path = Path(script_path)
        logger.info(f"⏰ [Bash] {full_path}")    

        cmd = ["bash", str(full_path)] + shlex.split(args)
        proc = subprocess.Popen(
            cmd,
            cwd=full_path.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {"proc": proc, "cmd": cmd, "script": str(full_path)}
    except Exception as e:
        logger.error(f"🚨 Erreur Bash : {script_path} : {e}")
        raise

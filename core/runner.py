#!/usr/bin/env python3
import subprocess
import sys
import os
import shlex
import yaml
from pathlib import Path
from utils.logger import get_logger
from utils.config import SCRIPT_DIR

logger = get_logger("Cron_Hub")

def run_python_script(script_path, args="", interpreter=None):
    try:
        if interpreter is None:
            logger.warning(f"🚨 Impossible de détecter le projet pour ce script → risque d’interpréteur incorrect")
            
        full_path = os.path.join(SCRIPT_DIR, script_path)
        cwd = Path(full_path).parent
        
        # Détection de projet (ex: brain_ops)
        project_root = None
        for parent in Path(full_path).parents:
            if parent.name == "brain_ops":
                project_root = parent
                break
        if not project_root:
            project_root = Path(full_path).parent.parent

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
        
        cmd = [interpreter or sys.executable, full_path] + shlex.split(args)

        logger.info(f"⏰ [Python] {full_path}")
        subprocess.run(cmd, env=env, cwd=cwd, check=True)
        #logger.info(f"🌞 Succès Python : {script_path}")
    except Exception as e:
        logger.error(f"🚨 Erreur Python {e}")
        raise
        


def run_bash_script(script_path, args=""):
    try:
        full_path = os.path.join(SCRIPT_DIR, script_path)
                   
        logger.info(f"⏰ [Bash] {full_path}")    
        cmd = ["bash", full_path] + shlex.split(args)
        subprocess.run(cmd, cwd=Path(full_path).parent, check=True)
        #logger.info(f"🌞 Succès Bash : {script_path}")
    except Exception as e:
        logger.error(f"🚨 Erreur Bash : {script_path} : {e}")

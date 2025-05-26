from pathlib import Path
import yaml
from typing import Optional
from utils.config import PROJECT_ROOT_FOLDERS, INTERPRETERS_PATH
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def load_interpreters_map(path=INTERPRETERS_PATH):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"⚠️ Impossible de charger venvs.yaml : {e}")
        return {}

def detect_project_name(script_path: str) -> Optional[str]:
    parts = Path(script_path).parts
    for marker in PROJECT_ROOT_FOLDERS:
        if marker in parts:
            idx = parts.index(marker)
            if len(parts) > idx + 1:
                print(f"Project detected: {parts[idx + 1]}")
                return parts[idx + 1]
    return None

def get_interpreter_from_project(script_path: str, source_file, interpreters_map: dict) -> str:
    project = source_file
    return interpreters_map.get(project)

def check_missing_interpreters(tasks_dir: Path, interpreters: dict):
    for yaml_file in tasks_dir.glob("*.yaml"):
        with open(yaml_file) as f:
            try:
                tasks = yaml.safe_load(f) or []
            except Exception as e:
                logger.warning(f"Can't read {yaml_file}: {e}")
                continue

        for task in tasks:
            if task.get("exec_type") != "python":
                continue

            interpreter = task.get("interpreter")
            if not interpreter:
                script_path = task.get("path")
                project = detect_project_name(script_path)
                found = interpreters.get(project)

                if not found:
                    logger.warning(
                        f"[{yaml_file.name}] Task '{task.get('name')}' (project='{project}') "
                        "has no interpreter defined → fallback will be used!"
                    )
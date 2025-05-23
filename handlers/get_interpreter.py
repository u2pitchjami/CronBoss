from pathlib import Path
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def load_interpreters_map(path="venvs.yaml"):
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"⚠️ Impossible de charger venvs.yaml : {e}")
        return {}

def detect_project_name(script_path: str) -> str:
    parts = Path(script_path).parts
    if "dev" in parts:
        idx = parts.index("dev")
        if len(parts) > idx + 1:
            return parts[idx + 1]  # ex: brain_ops
    return None

def get_interpreter_from_project(script_path: str, interpreters_map: dict) -> str:
    project = detect_project_name(script_path)
    return interpreters_map.get(project)
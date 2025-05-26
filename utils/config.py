# config.py
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Chargement du .env à la racine du projet
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# --- Fonctions utilitaires ---

def get_required(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        print(f"[CONFIG ERROR] La variable {key} est requise mais absente.")
        sys.exit(1)
    return value

def get_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in ("true", "1", "yes")

def get_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)

def get_int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"[CONFIG ERROR] La variable {key} doit être un entier.")
        sys.exit(1)

# --- Variables d'environnement accessibles globalement ---

SCRIPT_DIR = get_required("SCRIPT_DIR")
ENV_PYTHON = get_required("ENV_PYTHON")
INTERPRETERS_PATH = get_required("INTERPRETERS_PATH")


#LOGS
LOG_FILE_PATH = get_required("LOG_FILE_PATH")
LOG_ROTATION_DAYS = get_int("LOG_ROTATION_DAYS", 100)

CRON_INTERVAL_MINUTES = get_int("CRON_INTERVAL_MINUTES", 0)

PROJECT_ROOT_FOLDERS = ["dev", "bin"]

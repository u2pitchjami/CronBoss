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
DEFAULT_VENV = get_required("DEFAULT_VENV")
INTERPRETERS_PATH = get_required("INTERPRETERS_PATH")
TASKS_DIR = get_str("TASKS_DIR", "./tasks")

#LOGS
LOG_FILE_PATH = get_required("LOG_FILE_PATH")
LOG_ROTATION_DAYS = get_int("LOG_ROTATION_DAYS", 100)

CRON_INTERVAL_MINUTES = get_int("CRON_INTERVAL_MINUTES", 0)

WARNINGS_AS_FAILURE = get_str("WARNINGS_AS_FAILURE", False)
SEND_SUMMARY_DISCORD = get_str("SEND_SUMMARY_DISCORD", "false").lower() == "true"


DISCORD_WEBHOOK_URL = get_str("DISCORD_WEBHOOK_URL", "")
DEFAULT_NOTIFY_ON = get_str("DEFAULT_NOTIFY_ON", "none")

# Email (préparé pour plus tard)
SMTP_SERVER = get_str("SMTP_SERVER")
MAIL_FROM = get_str("MAIL_FROM")
MAIL_TO = get_str("MAIL_TO")

# Autres notifiers possibles (Slack, etc.)
SLACK_WEBHOOK_URL = get_str("SLACK_WEBHOOK_URL")

PROJECT_ROOT_FOLDERS = ["dev", "bin"]

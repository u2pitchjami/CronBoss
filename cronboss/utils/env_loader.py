from dotenv import load_dotenv, dotenv_values
from pathlib import Path

def load_project_env():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path, override=True, verbose=True)

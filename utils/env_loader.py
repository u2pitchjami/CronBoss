from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path, override=True, verbose=True)

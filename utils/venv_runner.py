#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Mapping, Sequence
import logging
import os
from pathlib import Path
import subprocess
import sys

# ────────────────────────────────────────────────────────────────────────────────
# Config par variables d'env (facile à changer sans toucher le script)
# - CRONBOSS_VENV_PYTHON : chemin vers le binaire Python du venv
# - CRONBOSS_ROOT_MARKER : nom de dossier "marqueur" pour détecter la racine projet
# ────────────────────────────────────────────────────────────────────────────────
VENV_PY_ENV = os.getenv("DEFAULT_VENV", "/home/pipo/envs/vcron/bin/python")
ROOT_MARKER = os.getenv("PROJECT_ROOT_FOLDERS", "bin")  # adapte si besoin

logger = logging.getLogger("venv_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def detect_project_root(target_script: Path) -> Path | None:
    for parent in target_script.parents:
        if parent.name == ROOT_MARKER:
            return parent
    return None


def build_env(project_root: Path) -> Mapping[str, str]:
    env = os.environ.copy()
    current_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{current_pp}" if current_pp else str(project_root)
    return env


def run_with_venv(venv_python: Path, target_script: Path, args: Sequence[str], env: Mapping[str, str]) -> int:
    cmd: list[str] = [str(venv_python), str(target_script), *args]  # RUF005 ok (unpacking)
    logger.info("⏰ Lancement via venv: %s", cmd)
    try:
        completed = subprocess.run(cmd, env=env, cwd=str(target_script.parent))
        return int(completed.returncode)
    except FileNotFoundError as exc:
        logger.error("❌ Binaire introuvable: %s", exc)
        return 127
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("❌ Échec d'exécution: %s", exc)
        return 1


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print("Usage: venv_runner.py /chemin/vers/script.py [args...]", file=sys.stderr)
        return 2

    target_script = Path(argv[1]).resolve()
    args: list[str] = list(argv[2:])

    if not target_script.exists() or not target_script.is_file():
        logger.error("❌ Script cible invalide: %s", target_script)
        return 2

    project_root = detect_project_root(target_script)
    if project_root is None:
        logger.error("❌ Impossible de détecter la racine projet (pas de dossier '%s' dans les parents)", ROOT_MARKER)
        return 2

    venv_python = Path(VENV_PY_ENV)
    if not venv_python.exists():
        logger.error("❌ Interpréteur de venv introuvable: %s", venv_python)
        return 2

    env = build_env(project_root)
    return run_with_venv(venv_python, target_script, args, env)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

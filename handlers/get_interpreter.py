# handlers/get_interpreter.py
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from utils.config import INTERPRETERS_PATH, PROJECT_ROOT_FOLDERS
from utils.logger import get_logger
from utils.types import InterpretersMap

logger = get_logger("CronHub")


def load_interpreters_map(path: str | Path = INTERPRETERS_PATH) -> InterpretersMap:
    """
    Charge le mapping des interpréteurs Python depuis un YAML (ex: venvs.yaml).

    Format attendu:
        project_name: /chemin/vers/venv/bin/python
    """
    p = Path(path)
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            logger.warning("⚠️ venvs.yaml vide ou non dict: %r", type(data).__name__)
            return {}
        # Filtre: on ne garde que les paires str->str
        out: dict[str, str] = {}
        for k, v in data.items():
            if isinstance(k, str) and isinstance(v, str) and k and v:
                out[k] = v
            else:
                logger.debug("Entrée ignorée dans venvs.yaml: %r -> %r", k, v)
        return out
    except FileNotFoundError:
        logger.warning("⚠️ Fichier venvs.yaml introuvable: %s", p)
        return {}
    except yaml.YAMLError as exc:
        logger.warning("⚠️ YAML invalide dans venvs.yaml: %s", exc)
        return {}
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("⚠️ Impossible de charger venvs.yaml (%s): %s", p, exc)
        return {}


def detect_project_name(script_path: str | Path) -> str | None:
    """
    Détecte le nom de projet à partir d'un chemin de script, en utilisant les dossiers marqueurs de
    PROJECT_ROOT_FOLDERS.

    Exemple: /home/me/dev/mixonaut/mixonaut/scripts/a.py avec marker 'dev' -> 'mixonaut'
    """
    parts = Path(script_path).parts
    for marker in PROJECT_ROOT_FOLDERS:
        if marker in parts:
            idx = parts.index(marker)
            if len(parts) > idx + 1:
                project = parts[idx + 1]
                logger.debug("Project detected: %s", project)
                return project
    return None


def get_interpreter_from_project(
    script_path: str | Path,
    source_file: str,
    interpreters_map: InterpretersMap,
) -> str | None:
    """
    Retourne l'interpréteur Python à utiliser pour un script.

    Stratégie:   1) le 'project' est d’abord le 'source_file' (nom du YAML sans extension)   2) sinon, tentative via
    detect_project_name(script_path)   3) sinon, None (le code appelant appliquera un fallback: DEFAULT_VENV, etc.)
    """
    # 1) mapping par nom de fichier YAML (source_file)
    if source_file and source_file in interpreters_map:
        return interpreters_map[source_file]

    # 2) détection par chemin
    detected = detect_project_name(script_path)
    if detected and detected in interpreters_map:
        return interpreters_map[detected]

    return None


def check_missing_interpreters(tasks_dir: Path, interpreters: InterpretersMap) -> None:
    """
    Parcourt les fichiers YAML d'un répertoire et avertit si des tâches Python.

    n'ont pas d'interpréteur résolu. Utilise le schéma YAML ACTUEL:
      - type: "python" | "bash"
      - script: str
      - interpreter: str (optionnel)
    """
    for yaml_file in tasks_dir.glob("*.yaml"):
        try:
            with yaml_file.open("r", encoding="utf-8") as f:
                loaded: Any = yaml.safe_load(f) or []
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Can't read %s: %s", yaml_file, exc)
            continue

        if not isinstance(loaded, list):
            logger.debug("%s ignoré (contenu non-liste: %s)", yaml_file.name, type(loaded).__name__)
            continue

        for task in loaded:
            if not isinstance(task, dict):
                continue

            # --- Aligné sur le YAML actuel ---
            ttype = task.get("type")
            if ttype != "python":
                continue

            interpreter = task.get("interpreter")
            if interpreter:  # déjà défini explicitement
                continue

            script_path = task.get("script")
            if not isinstance(script_path, str):
                logger.warning("[%s] Tâche sans 'script' valide: %r", yaml_file.name, task)
                continue

            # project name via source_file (nom de yaml) OU detect_project_name
            project = yaml_file.stem or detect_project_name(script_path)
            found = interpreters.get(project) if project else None

            if not found:
                task_name = task.get("name") or Path(script_path).name
                logger.warning(
                    "[%s] Task '%s' (project='%s') n'a pas d'interpréteur défini → fallback sera utilisé.",
                    yaml_file.name,
                    task_name,
                    project,
                )

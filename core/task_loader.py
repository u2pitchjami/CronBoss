#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import yaml

from utils.logger import get_logger
from utils.normalizer import normalize_task_dict
from utils.types import TaskWithSource

logger = get_logger("Cron_Hub")


def load_tasks_from_directory(task_dir: str | Path) -> list[TaskWithSource]:
    """
    Charge tous les fichiers YAML d'un répertoire, normalise chaque entrée et retourne une liste de tâches prêtes à
    l'emploi (TaskWithSource).
    """
    tasks_out: list[TaskWithSource] = []
    task_dir_path = Path(task_dir)

    for file in sorted(task_dir_path.glob("*.yaml")):
        file_id = file.stem
        try:
            with file.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            logger.error("❌ Erreur YAML dans %s : %s", file.name, exc)
            continue
        except OSError as exc:
            logger.error("❌ Erreur d'ouverture du fichier %s : %s", file, exc)
            continue

        if loaded is None:
            continue

        if not isinstance(loaded, list):
            logger.warning("⚠️ %s : contenu YAML non liste, ignoré (type: %s)", file.name, type(loaded).__name__)
            continue

        for raw in loaded:
            task = normalize_task_dict(raw, file_id)
            if task is None:
                # message déjà loggé dans normalizer
                continue
            tasks_out.append(task)

    return tasks_out

#!/usr/bin/env python3
from pathlib import Path
import yaml
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def load_tasks_from_directory(task_dir):
    all_tasks = []
    for file in Path(task_dir).glob("*.yaml"):
        file_id = file.stem
        with open(file, "r") as f:
            try:
                tasks = yaml.safe_load(f)
                for task in tasks:
                    task["source_file"] = file_id
                if isinstance(tasks, list):
                    all_tasks.extend(tasks)
            except yaml.YAMLError as e:
                logger.error(f"❌ Erreur YAML dans {file.name} : {e}")
    return all_tasks

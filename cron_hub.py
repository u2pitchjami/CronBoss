#!/usr/bin/env python3
import datetime
from pathlib import Path
from core.task_loader import load_tasks_from_directory
from core.scheduler import should_run
from core.runner import run_python_script, run_bash_script
from handlers.cleanup_logs import cleanup_multiple
from handlers.get_interpreter import load_interpreters_map, get_interpreter_from_project
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def main():
    now = datetime.datetime.now()
    hour = now.hour
    weekday = now.weekday()
    day = now.day

    logger.info(f"📅 CRONHUB {now.strftime('%A %d-%m-%Y %H:%M')}")
    interpreters = load_interpreters_map()
    tasks = load_tasks_from_directory("tasks")

    for task in tasks:
        if task.get("enabled", True) is False:
            logger.info(f"⏸️ Tâche désactivée (enabled: false) : {task.get('script')}")
            continue
        if should_run(task, hour, weekday, day):
            task_type = task.get("type")
            script = task.get("script")
            args = task.get("args", "")

            if task_type == "python":
                interpreter = task.get("interpreter") or get_interpreter_from_project(script, interpreters)
                run_python_script(script, args)
            elif task_type == "bash":
                run_bash_script(script, args)
            else:
                logger.warning(f"❓ Type inconnu : {task_type} pour {script}")
        if "cleanup" in task:
            paths = task["cleanup"].get("paths")
            if paths:
                cleanup_multiple(paths, task["cleanup"]["rule"])



    logger.info("🏁 CRONHUB : TERMINE ✅\n")

if __name__ == "__main__":
    main()

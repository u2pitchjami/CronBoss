#!/usr/bin/env python3
import datetime
import time
from pathlib import Path
from core.task_loader import load_tasks_from_directory
from core.scheduler import should_run, is_script_running, verifier_fichier
from core.runner import run_python_script, run_bash_script
from handlers.cleanup_logs import cleanup_multiple
from handlers.get_interpreter import load_interpreters_map, get_interpreter_from_project
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def format_duration(seconds):
    """Convertit une durée en secondes en minutes + secondes."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes} min {secs} sec"

def main():
    now = datetime.datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    day = now.day

    logger.info(f"📅 CRONHUB {now.strftime('%A %d-%m-%Y %H:%M')}")
    interpreters = load_interpreters_map()
    tasks = load_tasks_from_directory("tasks")

    script_error = False
    for task in tasks:
        if should_run(task, hour, minute, weekday, day):
            task_type = task.get("type")
            exclusive = task.get("exclusive", True)
            source_file = task.get("source_file")
            script = task.get("script")
            args = task.get("args", "")
            logger.info(f"🎞️ Projet : {source_file}")
            if task.get("enabled", True) is False:
                logger.info(f"⏸️ Tâche désactivée (enabled: false) : {task.get('script')}")
                continue
            else:
                if exclusive and is_script_running(script):
                    logger.info(f"🛝 Skip: {script} est déjà en cours.")
                    continue
                if not verifier_fichier(chemin=script):
                    logger.error(f"🛝 Script introuvable, vérifiez le yaml")
                    continue
                try:
                    start_time = time.time()
                    if task_type == "python":
                        interpreter = task.get("interpreter") or get_interpreter_from_project(script, source_file, interpreters)
                        run_python_script(script, args, interpreter)
                    elif task_type == "bash":
                        run_bash_script(script, args)
                    else:
                        logger.warning(f"❓ Type inconnu : {task_type} pour {script}")
                        
                    duration = time.time() - start_time
                except Exception as e:
                    script_error = True
                    continue
                finally:
                    if script_error:
                        logger.error(f"🚨 Erreur lors de l'exécution de la tâche {task.get('script')}: \n")
                    
                    logger.info(f"🌞 Tâche {task.get('script')} terminée avec succès en : {format_duration(duration)} \n")
                    
                    
        if "cleanup" in task:
            paths = task["cleanup"].get("paths")
            if paths:
                cleanup_multiple(paths, task["cleanup"]["rule"])



    logger.info("🏁 CRONHUB : TERMINE ✅\n")

if __name__ == "__main__":
    main()

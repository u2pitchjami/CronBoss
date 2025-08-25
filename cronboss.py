#!/usr/bin/env python3
import datetime
import time
from pathlib import Path
from utils.config import TASKS_DIR
from core.task_loader import load_tasks_from_directory
from handlers.get_interpreter import load_interpreters_map
from core.scheduler import should_run, is_script_running, verifier_fichier
from core.runner import run_python_script, run_bash_script
from handlers.cleanup_logs import cleanup_multiple
from utils.logger import get_logger
from notifiers.manager import NotifierManager
from core.task import Task
import time

logger = get_logger("CronHub")
notifier_manager = NotifierManager()

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
    raw_tasks = load_tasks_from_directory(TASKS_DIR)
    interpreters = load_interpreters_map()
    tasks = [Task(cfg, cfg.get("source_file", "unknown"), interpreters) for cfg in raw_tasks]
    
    running_tasks = []    
    for task in tasks:
        if task.enabled and task.should_run(hour, minute, weekday, day) and task.can_start():
            try:
                if task.type == "python":
                    handle = run_python_script(str(task.script), task.cwd, task.args, task.interpreter)
                elif task.type == "bash":
                    handle = run_bash_script(str(task.script), task.cwd, task.args)
                else:
                    logger.warning(f"❓ Type inconnu : {task.type} pour {task.script}")
                    continue

                task.start(handle)
                running_tasks.append(task)

            except Exception as e:
                logger.error(f"🚨 Impossible de lancer {task.script} : {e}")
                notifier_manager.notify(task, "failure", error=str(e))

        # Gestion du cleanup
        if task.cleanup:
            paths = task.cleanup.get("paths")
            if paths:
                cleanup_multiple(paths, task.cleanup["rule"])

    # Suivi des tâches en cours
    while running_tasks:
        still_running = []
        logger.debug(f"🚨 test : running_tasks {running_tasks}s")
        for task in running_tasks:
            logger.debug(f"🚨 test : {task.script} timeout {task.timeout}s")
            if task.proc.poll() is None:
                # Timeout async
                if task.timeout > 0 and (time.time() - task.start_time) > task.timeout:
                    task.proc.kill()
                    task.returncode = -1
                    task.stderr = f"⏱️ Timeout dépassé ({task.timeout}s)"
                    logger.error(f"🚨 {task.script} timeout après {task.timeout}s")
                    notifier_manager.notify(task, "failure", stderr=task.stderr)
                else:
                    still_running.append(task)
                    logger.debug(f"🚨 test2 : {task.script} timeout {task.timeout}s")
            else:
                # Terminé
                task.finish()
                status = task.get_status()

                if status == "failure" and task.attempts <= task.retries:
                    logger.warning(f"🔄 Retry {task.attempts}/{task.retries} pour {task.script}")
                    handle = run_python_script(str(task.script), task.args, task.interpreter) \
                        if task.type == "python" else run_bash_script(str(task.script), task.args)
                    task.start(handle)
                    still_running.append(task)
                else:
                    if task.is_success():
                        logger.info(f"🌞 {task.script} OK en {task.duration:.2f}s")
                    else:
                        logger.error(f"🚨 {task.script} KO (code {task.returncode})")

                    notifier_manager.notify(
                        task,
                        status,
                        stdout=task.stdout,
                        stderr=task.stderr,
                        duration=task.duration,
                        returncode=task.returncode
                    )

        running_tasks = still_running
        time.sleep(2)

        # === Résumé global des tâches ===
    if tasks:
        summary = {"success": 0, "success_with_warnings": 0, "failure": 0}
        total_duration = 0

        for task in tasks:
            status = task.get_status()
            if status not in summary:
                summary[status] = 0
            summary[status] += 1

            if hasattr(task, "duration"):
                total_duration += task.duration or 0

        logger.info(
            f"📊 RÉSUMÉ : ✅ {summary['success']} succès | "
            f"⚠️ {summary['success_with_warnings']} avec warnings | "
            f"❌ {summary['failure']} échecs | "
            f"⏱️ Durée totale : {total_duration:.2f}s"
        )

        notifier_manager.notify_summary({**summary, "total_duration": total_duration})

    logger.info("🏁 CRONHUB : TERMINE ✅\n")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import time

from core.runner import run_bash_script, run_python_script
from core.task import Task
from core.task_loader import load_tasks_from_directory
from handlers.cleanup_logs import cleanup_multiple
from handlers.get_interpreter import load_interpreters_map
from notifiers.manager import NotifierManager
from utils.audit import append_run_record
from utils.config import AUDIT_JSON, TASKS_DIR
from utils.logger import get_logger
from utils.types import SummaryPayload, TaskWithSource

logger = get_logger("CronBoss")
notifier_manager = NotifierManager()


def format_duration(seconds: float) -> str:
    """
    Convertit une durée en secondes en minutes + secondes.
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes} min {secs} sec"


def main() -> None:
    """
    Boucle principale :
    - charge les tâches YAML
    - résout les interpréteurs
    - planifie/lanche selon l'heure courante
    - suit l'exécution, gère retries/timeout
    - envoie les notifications et un résumé final
    """
    now = dt.datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    day = now.day

    logger.info("📅 CRONBOSS %s", now.strftime("%A %d-%m-%Y %H:%M"))

    # Chargement & préparation
    raw_tasks: list[TaskWithSource] = load_tasks_from_directory(TASKS_DIR)
    interpreters = load_interpreters_map()
    tasks: list[Task] = [Task(cfg, cfg.get("source_file", "unknown"), interpreters) for cfg in raw_tasks]

    running_tasks: list[Task] = []
    for task in tasks:
        # Planif
        if task.enabled and task.should_run(hour, minute, weekday, day) and task.can_start():
            try:
                if task.type == "python":
                    logger.info("🐍 Lancement de %s avec l'interpréteur %s", task.script, task.interpreter)
                    handle = run_python_script(str(task.script), task.cwd, task.args, task.interpreter)
                elif task.type == "bash":
                    handle = run_bash_script(str(task.script), task.cwd, task.args)
                else:
                    logger.warning("❓ Type inconnu : %s pour %s", task.type, task.script)
                    continue

                task.start(handle)
                if task.proc is not None:
                    running_tasks.append(task)
                else:
                    logger.info("⏭️ %s non démarrée (lock indisponible).", task.script)

            except Exception as exc:  # pylint: disable=broad-except
                logger.error("🚨 Impossible de lancer %s : %s", task.script, exc)
                notifier_manager.notify(task, "failure", error=str(exc))
                # libère le lock acquis par can_start()
                if getattr(task, "_task_lock_fh", None) is not None:
                    from utils.lock import release_task_lock

                    release_task_lock(task._task_lock_fh)
                    task._task_lock_fh = None

        # Cleanup éventuel (indépendant du lancement)
        if task.cleanup:
            paths = task.cleanup.get("paths")
            rule = task.cleanup.get("rule")
            if paths and rule:
                cleanup_multiple(paths, rule)

    # Suivi des tâches en cours
    while running_tasks:
        still_running: list[Task] = []

        for task in running_tasks:
            status = task.check_status()  # None | "success" | "failure" | "retry"

            if status is None:
                # Toujours en cours
                still_running.append(task)
                continue

            if status == "retry":
                logger.warning("🔄 Retry %s/%s pour %s", task.attempts, task.retries, task.script)
                try:
                    handle = (
                        run_python_script(str(task.script), task.cwd, task.args, task.interpreter)
                        if task.type == "python"
                        else run_bash_script(str(task.script), task.cwd, task.args)
                    )
                    task.start(handle)
                    if task.proc is not None:  # lock par tâche : peut refuser
                        still_running.append(task)
                    else:
                        logger.info("⏭️ Retry annulé (lock indisponible) pour %s", task.script)
                except Exception as exc:  # pylint: disable=broad-except
                    logger.error("🚨 Échec retry %s : %s", task.script, exc)
                    notifier_manager.notify(task, "failure", stderr=str(exc))
                continue

            # Ici: "success" ou "failure" -> on collecte proprement
            task.finish()

            final = task.get_status()

            if task.is_success():
                logger.info("🌞 %s OK en %.2fs", task.script, task.duration or 0.0)
            else:
                logger.error("🚨 %s KO (code %s)", task.script, task.returncode)

            append_run_record(
                AUDIT_JSON,
                {
                    "script": str(task.script),
                    "status": final,
                    "duration": float(task.duration or 0.0),
                    "returncode": task.returncode,
                    "source_file": task.source_file,
                    "stdout_tail": (task.stdout or "")[-400:] or None,
                    "stderr_tail": (task.stderr or "")[-400:] or None,
                },
            )

            notifier_manager.notify(
                task,
                final,
                stdout=task.stdout,
                stderr=task.stderr,
                duration=task.duration or 0.0,
                returncode=task.returncode,
            )

        running_tasks = still_running
        time.sleep(2)

    # === Résumé global des tâches ===
    if tasks:
        summary_counts: dict[str, int] = {"success": 0, "success_with_warnings": 0, "failure": 0}
        total_duration: float = 0.0

        for task in tasks:
            st = task.get_status()
            if st in summary_counts:
                summary_counts[st] += 1
            if task.duration is not None:
                total_duration += task.duration

        logger.info(
            "📊 RÉSUMÉ : ✅ %s succès | ⚠️ %s avec warnings | ❌ %s échecs | ⏱️ Durée totale : %.2fs",
            summary_counts["success"],
            summary_counts["success_with_warnings"],
            summary_counts["failure"],
            total_duration,
        )

        summary_payload: SummaryPayload = {
            "success": summary_counts["success"],
            "success_with_warnings": summary_counts["success_with_warnings"],
            "failure": summary_counts["failure"],
            "total_duration": total_duration,
        }
        notifier_manager.notify_summary(summary_payload)

    logger.info("🏁 CRONBOSS : TERMINE ✅\n")


if __name__ == "__main__":
    main()

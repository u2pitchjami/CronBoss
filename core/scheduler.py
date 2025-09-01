from __future__ import annotations

from pathlib import Path

import psutil

from utils.config import CRON_INTERVAL_MINUTES
from utils.logger import get_logger
from utils.types import DaysField, HoursField, MinutesField, TaskConfig  # TypedDict & unions

logger = get_logger("CronBoss")


def should_run(task: TaskConfig, hour: int, minute: int, weekday: int, day: int) -> bool:
    """
    Détermine si une tâche doit s'exécuter au tick courant.

    Hypothèses (via normalizer):
      - task["hours"] ∈ {"any", list[int]}
      - task["minutes"] ∈ list[int] (liste vide = pas de contrainte → "any")
      - task["days"] ∈ {"any", list[int] (jours du mois), {"weekday": list[int]}}

    :param task: Config de la tâche (normalisée).
    :param hour: Heure courante (0..23).
    :param minute: Minute courante (0..59).
    :param weekday: Jour de semaine courant (0=Mon .. 6=Sun).
    :param day: Jour du mois courant (1..31).
    :return: True si la tâche doit s'exécuter, False sinon.
    """
    # Heures
    hours: HoursField = task.get("hours", "any")
    match_hour = True if hours == "any" else hour in hours

    # Jours
    days: DaysField = task.get("days", "any")
    if days == "any":
        match_day = True
    elif isinstance(days, list):
        # liste => jours du mois
        match_day = day in days
    elif isinstance(days, dict) and "weekday" in days:
        # spécification par jour de semaine
        match_day = weekday in days.get("weekday", [])
    else:
        match_day = False

    # Minutes (rappel: [] = any)
    minutes: MinutesField = task.get("minutes", [])
    if not minutes:
        match_minute = True
    elif CRON_INTERVAL_MINUTES > 0:
        lower = (minute - (CRON_INTERVAL_MINUTES - 1)) % 60
        match_minute = any(((m - lower) % 60) < CRON_INTERVAL_MINUTES for m in minutes)
    else:
        match_minute = minute in minutes

    return match_hour and match_day and match_minute


def is_script_running(script_path: str) -> bool:
    """
    Vérifie via psutil si un process en cours contient `script_path` dans sa cmdline.

    :param script_path: Chemin du script recherché.
    """
    for proc in psutil.process_iter(["cmdline"]):
        try:
            cmdline: list[str] | None = proc.info.get("cmdline")
            if cmdline and script_path in " ".join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue
    return False


def verifier_fichier(chemin: str) -> bool:
    """
    Vérifie qu'un fichier existe, est lisible, et prêt à être utilisé.

    Args:
        chemin (str): Chemin vers le fichier à tester.

    Returns:
        bool: True si le fichier est valide, False sinon.
    """
    fichier = Path(chemin)

    if not fichier.exists():
        logger.error("Le fichier n'existe pas : %s", fichier)
        return False

    if not fichier.is_file():
        logger.error("Ce chemin n'est pas un fichier : %s", fichier)
        return False

    try:
        with fichier.open("r", encoding="utf-8"):
            pass
        logger.info("Fichier valide et lisible : %s", fichier)
        return True
    except PermissionError:
        logger.error("Pas les droits pour lire le fichier : %s", fichier)
    except Exception as err:  # pylint: disable=broad-except
        logger.exception("Erreur inattendue avec le fichier %s : %s", fichier, err)

    return False

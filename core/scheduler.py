import psutil
from pathlib import Path
from datetime import datetime
from utils.logger import get_logger
from utils.config import CRON_INTERVAL_MINUTES

logger = get_logger("Cron_Hub")

def should_run(task, hour, minute, weekday, day):
    # Heure
    hours = task.get("hours", "any")
    match_hour = hours == "any" or hour in hours
    # Jour
    days = task.get("days", "any")
    if days == "any":
        match_day = True
    elif isinstance(days, list):
        match_day = weekday in days or day in days
    elif isinstance(days, dict):
        match_day = (
            weekday in days.get("weekday", []) or
            day in days.get("day", [])
        )
    else:
        match_day = False

    # Minute
    minutes = task.get("minutes", "any")
    if minutes == "any":
        match_minute = True
    elif isinstance(minutes, list):
        if CRON_INTERVAL_MINUTES > 0:
            
            lower = (minute - (CRON_INTERVAL_MINUTES - 1)) % 60
            match_minute = any((m - lower) % 60 < CRON_INTERVAL_MINUTES for m in minutes)
        else:
            match_minute = minute in minutes
    else:
        match_minute = False

    return match_hour and match_day and match_minute

def is_script_running(script_path: str) -> bool:
    for proc in psutil.process_iter(['cmdline']):
        try:
            cmdline = proc.info['cmdline']
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
    except Exception as err:
        logger.exception("Erreur inattendue avec le fichier %s : %s", fichier, err)

    return False
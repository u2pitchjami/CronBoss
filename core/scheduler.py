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

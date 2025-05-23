#!/usr/bin/env python3
from utils.logger import get_logger

logger = get_logger("Cron_Hub")

def should_run(task, hour, weekday, day):
    hours = task.get("hours", "any")
    match_hour = hours == "any" or hour in hours

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

    return match_hour and match_day

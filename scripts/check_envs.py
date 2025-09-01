#!/usr/bin/env python3
from pathlib import Path

import yaml

from handlers.get_interpreter import check_missing_interpreters
from utils.config import INTERPRETERS_PATH


def main() -> None:
    interpreters = yaml.safe_load(open(INTERPRETERS_PATH)) or {}
    tasks_dir = Path("tasks")
    check_missing_interpreters(tasks_dir, interpreters)


if __name__ == "__main__":
    main()

from datetime import datetime
import logging
import os

from utils.config import LOG_FILE_PATH, LOG_ROTATION_DAYS
from utils.log_rotation import rotate_logs


def get_logger(name: str) -> logging.Logger:
    rotation_days = int(LOG_ROTATION_DAYS)

    os.makedirs(LOG_FILE_PATH, exist_ok=True)
    log_file = os.path.join(LOG_FILE_PATH, f"{datetime.now().strftime('%Y-%m-%d')}_{name.split('.')[0]}.log")

    rotate_logs(LOG_FILE_PATH, rotation_days, logf=log_file)

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s - PID:%(process)d] %(message)s")

        # Console
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # Fichier
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

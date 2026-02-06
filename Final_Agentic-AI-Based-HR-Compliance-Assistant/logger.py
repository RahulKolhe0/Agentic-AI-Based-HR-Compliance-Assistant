import logging
import os
from logging.handlers import RotatingFileHandler

import sys

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(message)s"))
handler.stream.reconfigure(encoding="utf-8")

# -------------------------------
# Log Folder Setup
# -------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

APP_LOG_PATH = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")

# -------------------------------
# Logger Config Function
# -------------------------------
def get_logger(name="HR_COMPLIANCE_BOT"):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        return logger

    # -------------------------------
    # Formatter
    # -------------------------------
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    # -------------------------------
    # App Log Handler
    # -------------------------------
    app_handler = RotatingFileHandler(
        APP_LOG_PATH,
        maxBytes=5_000_000,
        backupCount=3
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    # -------------------------------
    # Error Log Handler
    # -------------------------------
    error_handler = RotatingFileHandler(
        ERROR_LOG_PATH,
        maxBytes=2_000_000,
        backupCount=2
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # -------------------------------
    # Console Handler
    # -------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Attach handlers
    logger.addHandler(app_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger

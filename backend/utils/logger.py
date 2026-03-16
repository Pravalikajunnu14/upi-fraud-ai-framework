"""
logger.py
---------
Centralized logging for the Flask backend.
Writes to both console and a log file at backend/logs/app.log.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")


def get_logger(name: str = "upi_fraud") -> logging.Logger:
    """Return a configured logger instance."""
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:           # avoid duplicate handlers on hot-reload
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler – force UTF-8 so unicode chars don't crash on Windows
    import sys
    import io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ch = logging.StreamHandler(stream=utf8_stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    # Rotating file handler (5 MB × 3 backups)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger


logger = get_logger()

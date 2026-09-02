"""Configure the rotating application log in the resolved runtime state path."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


LOG_FILE_NAME = "nightscope.log"
LOG_HANDLER_NAME = "nightscope-file"


def configure_logging(runtime_dir: Path) -> Path:
    """Configure application logging with rotation and return the active log path."""
    log_dir = runtime_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / LOG_FILE_NAME

    root_logger = logging.getLogger()
    for handler in tuple(root_logger.handlers):
        if not isinstance(handler, RotatingFileHandler):
            continue
        if handler.get_name() != LOG_HANDLER_NAME:
            continue
        if Path(handler.baseFilename).resolve() == log_path.resolve():
            return log_path
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    file_handler.set_name(LOG_HANDLER_NAME)
    root_logger.addHandler(file_handler)
    return log_path

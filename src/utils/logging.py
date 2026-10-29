"""Logging utilities for VoiceDesk AI."""

from __future__ import annotations

import logging
import sys


def setup_logger(name: str = "voicedesk", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a standardized logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

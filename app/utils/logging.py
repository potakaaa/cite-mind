"""Centralized logging helpers for Cite Mind."""

from __future__ import annotations

import logging
import sys
from typing import Any

from config import settings


LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once for CLI, Streamlit, and tests."""
    selected_level = (level or settings.log_level).upper()
    numeric_level = getattr(logging, selected_level, logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root.addHandler(handler)

    root.setLevel(numeric_level)
    for handler in root.handlers:
        handler.setLevel(numeric_level)


def get_logger(name: str) -> logging.Logger:
    """Return an app logger after ensuring logging is configured."""
    configure_logging()
    return logging.getLogger(name)


def log_failure(
    logger: logging.Logger,
    stage: str,
    exc: Exception,
    **context: Any,
) -> None:
    """Log a stage failure with compact structured context."""
    context_text = " ".join(f"{key}={value!r}" for key, value in context.items() if value is not None)
    if context_text:
        logger.exception("%s failed: %s (%s)", stage, exc, context_text)
    else:
        logger.exception("%s failed: %s", stage, exc)

"""Structured logging configuration for INGOT using structlog."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path

import structlog


def configure_logging(base_dir: Path, verbosity: int = 0) -> None:
    """Configure structlog with stderr and rotating file handlers.

    Args:
        base_dir: Base directory for log files (e.g., ~/.ingot/).
        verbosity: 0=WARNING, 1=INFO (-v), 2=DEBUG (-vv).
    """
    log_level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }.get(verbosity, logging.DEBUG)

    # Ensure log directory exists
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"run-{date_str}.log"

    # Root logger setup
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # Stderr handler — WARNING+ only, human-readable
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root_logger.addHandler(stderr_handler)

    # Rotating file handler — DEBUG+, JSON via structlog
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(file_handler)

    # Shared processors for both handlers
    shared_processors: list[structlog.types.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib formatter for stderr (human-readable)
    stderr_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(),
        foreign_pre_chain=shared_processors,
    )
    stderr_handler.setFormatter(stderr_formatter)

    # Configure stdlib formatter for file (JSON)
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )
    file_handler.setFormatter(file_formatter)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog BoundLogger for the given name."""
    return structlog.get_logger(name)

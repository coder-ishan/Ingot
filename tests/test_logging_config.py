"""Tests for ingot.logging_config."""
import logging

import structlog

from ingot.logging_config import configure_logging, get_logger


def test_get_logger_returns_structlog_logger():
    logger = get_logger("ingot.test")
    # structlog BoundLogger wraps stdlib logger — check it's callable
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_configure_logging_verbosity_0_sets_warning(tmp_path):
    """Verbosity 0 should set root log level to WARNING."""
    configure_logging(tmp_path, verbosity=0)
    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_verbosity_1_sets_info(tmp_path):
    """Verbosity 1 (-v flag) should set root log level to INFO."""
    configure_logging(tmp_path, verbosity=1)
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_verbosity_2_sets_debug(tmp_path):
    """Verbosity 2 (-vv flag) should set root log level to DEBUG."""
    configure_logging(tmp_path, verbosity=2)
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_creates_log_dir(tmp_path):
    """configure_logging must create the logs/ subdirectory."""
    configure_logging(tmp_path, verbosity=0)
    assert (tmp_path / "logs").is_dir()


def test_configure_logging_high_verbosity_defaults_to_debug(tmp_path):
    """Verbosity values beyond 2 should default to DEBUG."""
    configure_logging(tmp_path, verbosity=99)
    assert logging.getLogger().level == logging.DEBUG

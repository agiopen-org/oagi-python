# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
import os
from io import StringIO
from unittest.mock import patch

import pytest

from oagi import Actor
from oagi.client import SyncClient
from oagi.exceptions import ConfigurationError
from oagi.logging import get_logger


@pytest.fixture
def clean_logging_state():
    """Clean and reset OAGI logging state before and after test."""

    def _clean_loggers():
        oagi_logger = logging.getLogger("oagi")
        oagi_logger.handlers.clear()
        oagi_logger.setLevel(logging.NOTSET)
        oagi_logger.propagate = True  # Reset propagate for tests

        # Clear child loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith("oagi."):
                logger = logging.getLogger(name)
                logger.handlers.clear()
                logger.setLevel(logging.NOTSET)

    _clean_loggers()
    yield
    _clean_loggers()


@pytest.fixture
def set_log_level():
    """Helper to set OAGI_LOG environment variable for tests."""

    def _set_level(level: str):
        os.environ["OAGI_LOG"] = level

    return _set_level


@pytest.fixture
def oagi_root_logger():
    """Get the root OAGI logger."""
    return logging.getLogger("oagi")


@pytest.fixture
def test_logger():
    """Create a test logger using get_logger."""
    return get_logger("test")


class TestLogging:
    @pytest.mark.usefixtures("clean_logging_state")
    def test_default_log_level(self, test_logger, oagi_root_logger):
        assert oagi_root_logger.level == logging.INFO
        assert test_logger.name == "oagi.test"

    @pytest.mark.parametrize(
        "env_value,expected_level",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("debug", logging.DEBUG),
            ("info", logging.INFO),
        ],
    )
    @pytest.mark.usefixtures("clean_logging_state")
    def test_log_level_configuration(
        self, env_value, expected_level, set_log_level, oagi_root_logger
    ):
        set_log_level(env_value)
        get_logger("test")
        assert oagi_root_logger.level == expected_level

    @pytest.mark.usefixtures("clean_logging_state")
    def test_invalid_log_level_defaults_to_info(self, set_log_level, oagi_root_logger):
        set_log_level("INVALID_LEVEL")
        get_logger("test")
        assert oagi_root_logger.level == logging.INFO

    @pytest.mark.usefixtures("clean_logging_state")
    def test_handler_configuration(self, test_logger, oagi_root_logger):
        assert len(oagi_root_logger.handlers) == 1
        handler = oagi_root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

        formatter = handler.formatter
        assert "%(asctime)s - %(name)s - %(levelname)s - %(message)s" in formatter._fmt

    @pytest.mark.usefixtures("clean_logging_state")
    def test_multiple_loggers_share_configuration(self, oagi_root_logger):
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert len(oagi_root_logger.handlers) == 1
        assert logger1.name == "oagi.module1"
        assert logger2.name == "oagi.module2"

    @pytest.mark.usefixtures("clean_logging_state")
    def test_log_level_change_after_initialization(
        self, set_log_level, oagi_root_logger
    ):
        set_log_level("INFO")
        get_logger("test1")
        assert oagi_root_logger.level == logging.INFO

        set_log_level("DEBUG")
        get_logger("test2")
        assert oagi_root_logger.level == logging.DEBUG

    @pytest.mark.parametrize(
        "log_level,should_appear,should_not_appear",
        [
            (
                "DEBUG",
                ["Debug message", "Info message", "Warning message", "Error message"],
                [],
            ),
            (
                "INFO",
                ["Info message", "Warning message", "Error message"],
                ["Debug message"],
            ),
            (
                "WARNING",
                ["Warning message", "Error message"],
                ["Debug message", "Info message"],
            ),
            (
                "ERROR",
                ["Error message"],
                ["Debug message", "Info message", "Warning message"],
            ),
        ],
    )
    @pytest.mark.usefixtures("clean_logging_state")
    @patch("sys.stderr", new_callable=StringIO)
    def test_log_filtering_by_level(
        self, mock_stderr, log_level, should_appear, should_not_appear, set_log_level
    ):
        set_log_level(log_level)
        logger = get_logger("test_module")

        self._log_all_levels(logger)
        output = mock_stderr.getvalue()

        self._assert_messages_in_output(
            output, should_appear, log_level, should_appear=True
        )
        self._assert_messages_in_output(
            output, should_not_appear, log_level, should_appear=False
        )

        if should_appear:
            assert "oagi.test_module" in output

    def _log_all_levels(self, logger):
        """Helper to log messages at all levels."""
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

    def _assert_messages_in_output(self, output, messages, log_level, should_appear):
        """Helper to assert messages appear or don't appear in output."""
        for message in messages:
            if should_appear:
                assert message in output, (
                    f"{message} should appear at {log_level} level"
                )
            else:
                assert message not in output, (
                    f"{message} should not appear at {log_level} level"
                )


class TestLoggingIntegration:
    @pytest.mark.usefixtures("clean_logging_state")
    def test_sync_client_logging(self, api_env, caplog, set_log_level):
        set_log_level("INFO")

        with caplog.at_level(logging.INFO, logger="oagi"):
            client = SyncClient()
            client.close()

        expected_msg = f"SyncClient initialized with base_url: {api_env['base_url']}"
        assert expected_msg in caplog.text
        assert any("oagi.sync_client" in record.name for record in caplog.records)

    @pytest.mark.parametrize(
        "log_level,task_desc,max_steps,expected_messages,unexpected_messages",
        [
            (
                "INFO",
                "Test task",
                3,
                ["Task initialized: 'Test task' (max_steps: 3)"],
                [],
            ),
            (
                "ERROR",
                "Error test",
                20,
                [],
                ["Task initialized", "SyncClient initialized"],
            ),
        ],
    )
    @pytest.mark.usefixtures("clean_logging_state")
    def test_task_logging_levels(
        self,
        api_env,
        caplog,
        log_level,
        task_desc,
        max_steps,
        expected_messages,
        unexpected_messages,
        set_log_level,
    ):
        set_log_level(log_level)

        with caplog.at_level(getattr(logging, log_level), logger="oagi"):
            with patch("oagi.client.sync.OpenAI"):
                task = Actor()
                task.init_task(task_desc, max_steps=max_steps)
                task.close()

        for msg in expected_messages:
            assert msg in caplog.text, f"Expected '{msg}' in logs"

        for msg in unexpected_messages:
            assert msg not in caplog.text, f"Did not expect '{msg}' in logs"

    @pytest.mark.usefixtures("clean_logging_state")
    def test_no_logging_with_invalid_config(self, caplog, set_log_level):
        os.environ.pop("OAGI_BASE_URL", None)
        os.environ.pop("OAGI_API_KEY", None)
        set_log_level("INFO")

        with caplog.at_level(logging.INFO, logger="oagi"):
            with pytest.raises(ConfigurationError):
                SyncClient()

        assert "SyncClient initialized" not in caplog.text

    @pytest.mark.usefixtures("clean_logging_state")
    def test_logger_namespace_isolation(self, set_log_level, oagi_root_logger):
        set_log_level("DEBUG")
        get_logger("test")

        other_logger = logging.getLogger("other.module")
        other_logger.setLevel(logging.WARNING)

        assert oagi_root_logger.level == logging.DEBUG
        assert other_logger.level == logging.WARNING

        root_logger = logging.getLogger()
        assert root_logger.level != logging.DEBUG

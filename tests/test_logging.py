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
from unittest.mock import Mock, patch

import pytest

from oagi import ShortTask
from oagi.exceptions import ConfigurationError
from oagi.logging import get_logger
from oagi.screenshot_maker import MockImage
from oagi.sync_client import SyncClient


class TestLogging:
    def setup_method(self):
        # Clear environment variables and reset logging state
        if "OAGI_LOG" in os.environ:
            del os.environ["OAGI_LOG"]

        # Clear any existing oagi loggers
        oagi_logger = logging.getLogger("oagi")
        oagi_logger.handlers.clear()
        oagi_logger.setLevel(logging.NOTSET)

        # Clear any child loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith("oagi."):
                logger = logging.getLogger(name)
                logger.handlers.clear()
                logger.setLevel(logging.NOTSET)

    def test_default_log_level(self):
        logger = get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.INFO
        assert logger.name == "oagi.test"

    @pytest.mark.parametrize(
        "env_value,expected_level",
        [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
            ("debug", logging.DEBUG),  # Case insensitive
            ("info", logging.INFO),  # Case insensitive
        ],
    )
    def test_log_level_configuration(self, env_value, expected_level):
        """Test that log level is correctly set from environment variable."""
        os.environ["OAGI_LOG"] = env_value
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == expected_level

    def test_invalid_log_level_defaults_to_info(self):
        os.environ["OAGI_LOG"] = "INVALID_LEVEL"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.INFO

    def test_handler_configuration(self):
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert len(oagi_root.handlers) == 1
        handler = oagi_root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)

        # Check formatter
        formatter = handler.formatter
        assert "%(asctime)s - %(name)s - %(levelname)s - %(message)s" in formatter._fmt

    def test_multiple_loggers_share_configuration(self):
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        oagi_root = logging.getLogger("oagi")

        # Should only have one handler
        assert len(oagi_root.handlers) == 1

        # Both loggers should be under the same root
        assert logger1.name == "oagi.module1"
        assert logger2.name == "oagi.module2"

    def test_log_level_change_after_initialization(self):
        # First initialization with INFO
        os.environ["OAGI_LOG"] = "INFO"
        get_logger("test1")
        oagi_root = logging.getLogger("oagi")
        assert oagi_root.level == logging.INFO

        # Change environment and create new logger
        os.environ["OAGI_LOG"] = "DEBUG"
        get_logger("test2")

        # Level should be updated
        assert oagi_root.level == logging.DEBUG

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
    @patch("sys.stderr", new_callable=StringIO)
    def test_log_filtering_by_level(
        self, mock_stderr, log_level, should_appear, should_not_appear
    ):
        """Test that log messages are correctly filtered based on log level."""
        os.environ["OAGI_LOG"] = log_level
        logger = get_logger("test_module")

        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = mock_stderr.getvalue()

        # Check messages that should appear
        for message in should_appear:
            assert message in output, f"{message} should appear at {log_level} level"

        # Check messages that should not appear
        for message in should_not_appear:
            assert message not in output, (
                f"{message} should not appear at {log_level} level"
            )

        # Check logger name in output if any messages appear
        if should_appear:
            assert "oagi.test_module" in output


class TestLoggingIntegration:
    def setup_method(self):
        # Clear any existing oagi loggers
        oagi_logger = logging.getLogger("oagi")
        oagi_logger.handlers.clear()
        oagi_logger.setLevel(logging.NOTSET)

        # Clear any child loggers
        for name in list(logging.Logger.manager.loggerDict.keys()):
            if name.startswith("oagi."):
                logger = logging.getLogger(name)
                logger.handlers.clear()
                logger.setLevel(logging.NOTSET)

    def test_sync_client_logging(self, api_env, caplog):
        """Test that SyncClient logs initialization correctly."""
        os.environ["OAGI_LOG"] = "INFO"

        with caplog.at_level(logging.INFO, logger="oagi"):
            client = SyncClient()
            client.close()

        assert (
            f"SyncClient initialized with base_url: {api_env['base_url']}"
            in caplog.text
        )
        assert any("oagi.sync_client" in record.name for record in caplog.records)

    @pytest.mark.parametrize(
        "log_level,task_desc,should_have_step,expected_messages,unexpected_messages",
        [
            (
                "INFO",
                "Test task",
                False,
                ["Task initialized: 'Test task' (max_steps: 3)"],
                [],
            ),
            (
                "DEBUG",
                "Debug test",
                True,
                [
                    "Executing step for task",
                    "Making API request to /v1/message",
                    "Request includes task_description: True",
                ],
                [],
            ),
            (
                "ERROR",
                "Error test",
                "error",  # Special case - will trigger error
                ["Error during step execution"],
                ["Task initialized", "SyncClient initialized"],
            ),
        ],
    )
    def test_task_logging_levels(
        self,
        mock_httpx_client_class,
        mock_httpx_client,
        api_env,
        api_response_init_task,
        http_status_error,
        caplog,
        log_level,
        task_desc,
        should_have_step,
        expected_messages,
        unexpected_messages,
    ):
        """Test ShortTask logging at different levels."""
        os.environ["OAGI_LOG"] = log_level

        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        response_data = api_response_init_task.copy()
        response_data["task_description"] = task_desc
        mock_response.json.return_value = response_data

        if should_have_step == "error":
            # First call succeeds, second fails
            mock_httpx_client.post.side_effect = [mock_response, http_status_error]
        else:
            mock_httpx_client.post.return_value = mock_response

        with caplog.at_level(getattr(logging, log_level), logger="oagi"):
            task = ShortTask()

            if log_level == "INFO":
                task.init_task(task_desc, max_steps=3)
            else:
                task.init_task(task_desc)

            if should_have_step == "error":
                try:
                    task.step(MockImage())
                except Exception:
                    pass  # Expected to fail
            elif should_have_step:
                task.step(MockImage())

            task.close()

        # Check expected messages
        for msg in expected_messages:
            assert msg in caplog.text, f"Expected '{msg}' in logs"

        # Check unexpected messages
        for msg in unexpected_messages:
            assert msg not in caplog.text, f"Did not expect '{msg}' in logs"

    def test_no_logging_with_invalid_config(self, caplog):
        # Don't set OAGI_BASE_URL or OAGI_API_KEY to trigger errors
        os.environ["OAGI_LOG"] = "INFO"

        with caplog.at_level(logging.INFO, logger="oagi"):
            try:
                SyncClient()
            except ConfigurationError:
                pass  # Expected to fail

        # Should not have any successful initialization logs
        assert "SyncClient initialized" not in caplog.text

    def test_logger_namespace_isolation(self):
        """Test that OAGI loggers don't interfere with other loggers"""
        os.environ["OAGI_LOG"] = "DEBUG"

        # Create an OAGI logger
        get_logger("test")

        # Create a regular logger
        other_logger = logging.getLogger("other.module")
        other_logger.setLevel(logging.WARNING)

        oagi_root = logging.getLogger("oagi")

        # OAGI should be at DEBUG level
        assert oagi_root.level == logging.DEBUG

        # Other logger should remain unaffected
        assert other_logger.level == logging.WARNING

        # Root logger should remain unaffected
        root_logger = logging.getLogger()
        assert root_logger.level != logging.DEBUG

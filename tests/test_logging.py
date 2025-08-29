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

from oagi.logging import get_logger


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

    def test_debug_log_level(self):
        os.environ["OAGI_LOG"] = "DEBUG"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.DEBUG

    def test_info_log_level(self):
        os.environ["OAGI_LOG"] = "INFO"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.INFO

    def test_warning_log_level(self):
        os.environ["OAGI_LOG"] = "WARNING"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.WARNING

    def test_error_log_level(self):
        os.environ["OAGI_LOG"] = "ERROR"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.ERROR

    def test_critical_log_level(self):
        os.environ["OAGI_LOG"] = "CRITICAL"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.CRITICAL

    def test_case_insensitive_log_level(self):
        os.environ["OAGI_LOG"] = "debug"
        get_logger("test")
        oagi_root = logging.getLogger("oagi")

        assert oagi_root.level == logging.DEBUG

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

    @patch("sys.stderr", new_callable=StringIO)
    def test_actual_logging_output(self, mock_stderr):
        os.environ["OAGI_LOG"] = "DEBUG"
        logger = get_logger("test_module")

        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = mock_stderr.getvalue()

        # All messages should appear at DEBUG level
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output

        # Check logger name in output
        assert "oagi.test_module" in output

    @patch("sys.stderr", new_callable=StringIO)
    def test_log_filtering_by_level(self, mock_stderr):
        os.environ["OAGI_LOG"] = "WARNING"
        logger = get_logger("test_module")

        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = mock_stderr.getvalue()

        # Only WARNING and ERROR should appear
        assert "Debug message" not in output
        assert "Info message" not in output
        assert "Warning message" in output
        assert "Error message" in output


class TestLoggingIntegration:
    def setup_method(self):
        # Clear environment variables and reset logging state
        for key in ["OAGI_LOG", "OAGI_BASE_URL", "OAGI_API_KEY"]:
            if key in os.environ:
                del os.environ[key]

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

    def test_sync_client_logging(self, caplog):
        os.environ["OAGI_LOG"] = "INFO"
        os.environ["OAGI_BASE_URL"] = "https://api.example.com"
        os.environ["OAGI_API_KEY"] = "test-key"

        with caplog.at_level(logging.INFO, logger="oagi"):
            from oagi.sync_client import SyncClient

            client = SyncClient()
            client.close()

        assert (
            "SyncClient initialized with base_url: https://api.example.com"
            in caplog.text
        )
        assert any("oagi.sync_client" in record.name for record in caplog.records)

    def test_short_task_logging(self, caplog):
        os.environ["OAGI_LOG"] = "INFO"
        os.environ["OAGI_BASE_URL"] = "https://api.example.com"
        os.environ["OAGI_API_KEY"] = "test-key"

        with caplog.at_level(logging.INFO, logger="oagi"):
            from oagi.short_task import ShortTask

            task = ShortTask()
            task.init_task("Test task", max_steps=3)
            task.close()

        assert "Task initialized: 'Test task' (max_steps: 3)" in caplog.text
        assert any("oagi.short_task" in record.name for record in caplog.records)

    def test_debug_level_integration(self, caplog):
        os.environ["OAGI_LOG"] = "DEBUG"
        os.environ["OAGI_BASE_URL"] = "https://api.example.com"
        os.environ["OAGI_API_KEY"] = "test-key"

        with caplog.at_level(logging.DEBUG, logger="oagi"):
            from oagi.screenshot_maker import MockImage
            from oagi.short_task import ShortTask

            task = ShortTask()
            task.init_task("Debug test")

            try:
                # This will fail with network error but should show debug logs
                task.step(MockImage())
            except Exception:
                pass  # Expected to fail

            task.close()

        # Should contain debug messages
        assert "Executing step for task" in caplog.text
        assert "Making API request to /v1/message" in caplog.text
        assert "Request includes task_description: True" in caplog.text

    def test_error_level_integration(self, caplog):
        os.environ["OAGI_LOG"] = "ERROR"
        os.environ["OAGI_BASE_URL"] = "https://api.example.com"
        os.environ["OAGI_API_KEY"] = "test-key"

        with caplog.at_level(logging.ERROR, logger="oagi"):
            from oagi.screenshot_maker import MockImage
            from oagi.short_task import ShortTask

            task = ShortTask()
            task.init_task("Error test")

            try:
                # This will fail with network error
                task.step(MockImage())
            except Exception:
                pass  # Expected to fail

            task.close()

        # Should only contain error messages, no info or debug
        assert "Task initialized" not in caplog.text
        assert "SyncClient initialized" not in caplog.text
        assert "Error during step execution" in caplog.text

    def test_no_logging_with_invalid_config(self, caplog):
        # Don't set OAGI_BASE_URL or OAGI_API_KEY to trigger errors
        os.environ["OAGI_LOG"] = "INFO"

        with caplog.at_level(logging.INFO, logger="oagi"):
            from oagi.sync_client import SyncClient

            try:
                SyncClient()
            except ValueError:
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

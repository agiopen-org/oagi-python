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
from oagi.client import SyncClient
from oagi.exceptions import ConfigurationError
from oagi.logging import get_logger

from .conftest import MockImage


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
                    "Making API request to /v2/message",
                    "Request includes task_description: True",
                ],
                [],
            ),
            (
                "ERROR",
                "Error test",
                "error",
                ["Error during step execution"],
                ["Task initialized", "SyncClient initialized"],
            ),
        ],
    )
    @pytest.mark.usefixtures("clean_logging_state")
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
        set_log_level,
    ):
        set_log_level(log_level)

        mock_response = self._create_mock_response(api_response_init_task, task_desc)
        self._setup_mock_client_behavior(
            mock_httpx_client, mock_response, should_have_step, http_status_error
        )

        with caplog.at_level(getattr(logging, log_level), logger="oagi"):
            self._execute_task_scenario(task_desc, log_level, should_have_step)

        self._assert_log_messages(caplog.text, expected_messages, unexpected_messages)

    def _create_mock_response(self, api_response_init_task, task_desc):
        """Helper to create mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = 200
        response_data = api_response_init_task.copy()
        response_data["task_description"] = task_desc
        mock_response.json.return_value = response_data
        return mock_response

    def _setup_mock_client_behavior(
        self, mock_httpx_client, mock_response, should_have_step, http_status_error
    ):
        """Helper to setup mock client behavior based on test scenario."""
        # V2 API: Mock S3 upload flow
        mock_upload_response = Mock()
        mock_upload_response.status_code = 200
        mock_upload_response.json.return_value = {
            "url": "https://s3.amazonaws.com/presigned-url",
            "uuid": "test-uuid-123",
            "expires_at": 1677652888,
            "file_expires_at": 1677739288,
            "download_url": "https://cdn.example.com/test-uuid-123",
        }
        mock_httpx_client.get.return_value = mock_upload_response

        mock_s3_response = Mock()
        mock_s3_response.status_code = 200
        mock_s3_response.raise_for_status = Mock()

        if should_have_step == "error":
            # V2 API: Make the POST call fail immediately
            mock_httpx_client.post.side_effect = http_status_error
        else:
            mock_httpx_client.post.return_value = mock_response

    def _execute_task_scenario(self, task_desc, log_level, should_have_step):
        """Helper to execute the task scenario."""
        task = ShortTask()

        if log_level == "INFO":
            task.init_task(task_desc, max_steps=3)
        else:
            task.init_task(task_desc)

        if should_have_step == "error":
            try:
                # V2 API: Mock upload_client for S3 upload
                with patch.object(task.client, "upload_client") as mock_upload_client:
                    mock_s3_response = Mock()
                    mock_s3_response.raise_for_status = Mock()
                    mock_upload_client.put.return_value = mock_s3_response
                    task.step(MockImage())
            except Exception:
                pass  # Expected to fail
        elif should_have_step:
            # V2 API: Mock upload_client for S3 upload
            with patch.object(task.client, "upload_client") as mock_upload_client:
                mock_s3_response = Mock()
                mock_s3_response.raise_for_status = Mock()
                mock_upload_client.put.return_value = mock_s3_response
                task.step(MockImage())

        task.close()

    def _assert_log_messages(self, log_text, expected_messages, unexpected_messages):
        """Helper to assert expected and unexpected messages in logs."""
        for msg in expected_messages:
            assert msg in log_text, f"Expected '{msg}' in logs"

        for msg in unexpected_messages:
            assert msg not in log_text, f"Did not expect '{msg}' in logs"

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

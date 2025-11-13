# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

from unittest.mock import Mock, patch

import pytest

from oagi.cli.main import main


@pytest.fixture
def mock_sys_exit():
    with patch("sys.exit") as mock_exit:
        yield mock_exit


class TestVersion:
    def test_displays_version_info(self, capsys):
        with patch("sys.argv", ["oagi", "version"]):
            main()

        captured = capsys.readouterr()
        assert "OAGI SDK version:" in captured.out
        assert "Python version:" in captured.out
        assert "Platform:" in captured.out


class TestConfig:
    def test_shows_config_with_masked_api_key(self, capsys, monkeypatch):
        monkeypatch.setenv("OAGI_API_KEY", "sk-1234567890abcdef")
        monkeypatch.setenv("OAGI_BASE_URL", "https://custom.api")

        with patch("sys.argv", ["oagi", "config", "show"]):
            main()

        captured = capsys.readouterr()
        assert "sk-12345..." in captured.out
        assert "sk-1234567890abcdef" not in captured.out
        assert "https://custom.api" in captured.out


class TestServerStart:
    def test_missing_dependencies_shows_error(self, mock_sys_exit):
        with (
            patch("sys.argv", ["oagi", "server", "start"]),
            patch("oagi.cli.server.check_optional_dependency") as mock_check,
        ):
            mock_check.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                main()

    def test_cli_flags_passed_to_server(self, monkeypatch):
        monkeypatch.setenv("OAGI_API_KEY", "test-key")

        with (
            patch(
                "sys.argv",
                ["oagi", "server", "start", "--host", "0.0.0.0", "--port", "9000"],
            ),
            patch("oagi.cli.server.check_optional_dependency"),
            patch("oagi.server.config.ServerConfig") as mock_config_class,
            patch("oagi.server.create_app"),
            patch("uvicorn.run") as mock_run,
        ):
            mock_config = Mock()
            mock_config.server_host = "0.0.0.0"
            mock_config.server_port = 9000
            mock_config.oagi_base_url = "https://api.agiopen.org"
            mock_config.default_model = "lux-v1"
            mock_config_class.return_value = mock_config

            main()

            mock_run.assert_called_once()
            assert mock_run.call_args[1]["host"] == "0.0.0.0"
            assert mock_run.call_args[1]["port"] == 9000


class TestAgentRun:
    def test_missing_dependencies_shows_error(self):
        with (
            patch("sys.argv", ["oagi", "agent", "run", "test"]),
            patch("oagi.cli.agent.check_optional_dependency") as mock_check,
        ):
            mock_check.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                main()

    def test_missing_api_key_shows_error(self, capsys, mock_sys_exit, monkeypatch):
        monkeypatch.delenv("OAGI_API_KEY", raising=False)

        with (
            patch("sys.argv", ["oagi", "agent", "run", "test"]),
            patch("oagi.cli.agent.check_optional_dependency"),
        ):
            main()

        captured = capsys.readouterr()
        assert "OAGI API key not provided" in captured.err

    def test_cli_flags_override_defaults(self, capsys, monkeypatch, mock_sys_exit):
        monkeypatch.setenv("OAGI_API_KEY", "test-key")

        with (
            patch(
                "sys.argv",
                [
                    "oagi",
                    "agent",
                    "run",
                    "test",
                    "--model",
                    "custom",
                    "--max-steps",
                    "50",
                ],
            ),
            patch("oagi.cli.agent.check_optional_dependency"),
            patch("oagi.agent.default.AsyncDefaultAgent"),
            patch(
                "oagi.handler.async_pyautogui_action_handler.AsyncPyautoguiActionHandler"
            ),
            patch("oagi.handler.async_screenshot_maker.AsyncScreenshotMaker"),
            patch("asyncio.run", return_value=True),
        ):
            main()

        captured = capsys.readouterr()
        assert "Model: custom" in captured.out
        assert "Max steps: 50" in captured.out

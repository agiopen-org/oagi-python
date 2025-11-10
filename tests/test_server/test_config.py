import os

import pytest

from oagi.server import ServerConfig


def test_server_config_loads():
    os.environ["OAGI_API_KEY"] = "test-key"

    config = ServerConfig()
    assert config.oagi_api_key == "test-key"
    assert config.server_port == 8000


def test_server_config_requires_api_key():
    os.environ.pop("OAGI_API_KEY", None)

    with pytest.raises(Exception):
        ServerConfig()

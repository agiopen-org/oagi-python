"""Server configuration using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseSettings):
    # OAGI API settings
    oagi_api_key: str = Field(..., alias="OAGI_API_KEY")
    oagi_base_url: str = Field(default="https://api.agiopen.org", alias="OAGI_BASE_URL")

    # Server settings
    server_host: str = Field(default="0.0.0.0", alias="OAGI_SERVER_HOST")
    server_port: int = Field(default=8000, alias="OAGI_SERVER_PORT")
    cors_allowed_origins: str = Field(default="*", alias="OAGI_CORS_ORIGINS")

    # Session settings
    session_timeout_seconds: float = Field(default=10.0)

    # Model settings
    default_model: str = Field(default="lux-v1", alias="OAGI_DEFAULT_MODEL")
    default_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # Agent settings
    max_steps: int = Field(default=30, alias="OAGI_MAX_STEPS", ge=1, le=100)

    # Socket.IO settings
    socketio_path: str = Field(default="/socket.io")
    socketio_timeout: float = Field(default=30.0)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "populate_by_name": True,
        "extra": "ignore",
    }

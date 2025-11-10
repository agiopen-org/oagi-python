# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
from datetime import datetime
from typing import Any

from ..exceptions import check_optional_dependency
from .config import ServerConfig
from .models import SessionStatusData
from .session_store import session_store
from .socketio_server import socket_app

check_optional_dependency("fastapi", "Server features", "server")
check_optional_dependency("uvicorn", "Server features", "server")

import uvicorn  # noqa: E402
from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_app(config: ServerConfig | None = None) -> FastAPI:
    if config is None:
        config = ServerConfig()

    app = FastAPI(
        title="OAGI Socket.IO Server",
        description="Real-time task automation server for OAGI SDK",
        version="0.1.0",
    )

    cors_origins = (
        config.cors_allowed_origins.split(",")
        if config.cors_allowed_origins != "*"
        else ["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": "OAGI Socket.IO Server",
            "version": "0.1.0",
            "status": "running",
        }

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        return {
            "status": "healthy",
            "server": {
                "name": "OAGI Socket.IO Server",
                "version": "0.1.0",
            },
            "config": {
                "base_url": config.oagi_base_url,
                "default_model": config.default_model,
            },
            "sessions": {
                "active": len(session_store.sessions),
                "connected": sum(
                    1 for s in session_store.sessions.values() if s.socket_id
                ),
            },
        }

    @app.get("/sessions")
    async def list_sessions() -> dict[str, Any]:
        return {
            "sessions": session_store.list_sessions(),
            "total": len(session_store.sessions),
        }

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> SessionStatusData:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        return SessionStatusData(
            session_id=session.session_id,
            status=session.status,  # type: ignore
            instruction=session.instruction,
            created_at=session.created_at,
            actions_executed=session.actions_executed,
            last_activity=datetime.fromtimestamp(session.last_activity).isoformat(),
        )

    @app.delete("/sessions/{session_id}")
    async def delete_session(session_id: str) -> dict[str, str]:
        session = session_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        if session.oagi_client:
            try:
                await session.oagi_client.close()
            except Exception as e:
                logger.warning(f"Error closing OAGI client: {e}")

        deleted = session_store.delete_session(session_id)
        if deleted:
            return {"message": f"Session {session_id} deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete session")

    @app.post("/sessions/cleanup")
    async def cleanup_sessions(timeout_hours: float = 1.0) -> dict[str, Any]:
        timeout_seconds = timeout_hours * 3600
        cleaned = session_store.cleanup_inactive_sessions(timeout_seconds)
        return {
            "cleaned": cleaned,
            "remaining": len(session_store.sessions),
        }

    # Mount Socket.IO application
    app.mount("/", socket_app)

    logger.info(
        f"Server created - will listen on {config.server_host}:{config.server_port}"
    )

    return app


if __name__ == "__main__":
    config = ServerConfig()
    app = create_app(config)
    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info",
    )

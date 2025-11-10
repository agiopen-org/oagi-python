# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import secrets
from datetime import datetime
from typing import Any
from uuid import uuid4


class Session:
    def __init__(
        self,
        session_id: str,
        instruction: str,
        mode: str = "actor",
        model: str = "lux-v1",
        temperature: float = 0.0,
    ):
        self.session_id: str = session_id
        self.instruction: str = instruction
        self.mode: str = mode
        self.model: str = model
        self.temperature: float = temperature

        # OAGI task state
        self.task_id: str = uuid4().hex
        self.message_history: list[dict[str, Any]] = []
        self.current_screenshot_url: str | None = None

        # Socket state
        self.socket_id: str | None = None
        self.namespace: str | None = None
        self.last_activity: float = datetime.now().timestamp()

        # Status tracking
        self.status: str = "initialized"
        self.created_at: str = datetime.now().isoformat()
        self.actions_executed: int = 0

        # OAGI client reference
        self.oagi_client: Any | None = None


class SessionStore:
    def __init__(self):
        self.sessions: dict[str, Session] = {}

    def create_session(
        self,
        instruction: str,
        mode: str = "actor",
        model: str = "lux-v1",
        temperature: float = 0.0,
        session_id: str | None = None,
    ) -> str:
        if session_id is None:
            session_id = f"ses_{secrets.token_urlsafe(16)}"

        session = Session(session_id, instruction, mode, model, temperature)
        self.sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def get_session_by_socket_id(self, socket_id: str) -> Session | None:
        for session in self.sessions.values():
            if session.socket_id == socket_id:
                return session
        return None

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions.pop(session_id)
            return True
        return False

    def update_activity(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = datetime.now().timestamp()

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": session.session_id,
                "status": session.status,
                "instruction": session.instruction,
                "created_at": session.created_at,
                "actions_executed": session.actions_executed,
                "connected": session.socket_id is not None,
            }
            for session in self.sessions.values()
        ]

    def cleanup_inactive_sessions(self, timeout_seconds: float) -> int:
        current_time = datetime.now().timestamp()
        sessions_to_delete = []

        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > timeout_seconds:
                sessions_to_delete.append(session_id)

        for session_id in sessions_to_delete:
            self.delete_session(session_id)

        return len(sessions_to_delete)


# Global instance
session_store = SessionStore()

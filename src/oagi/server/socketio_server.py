# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio
import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from ..agent import AsyncDefaultAgent, create_agent
from ..client import AsyncClient
from ..exceptions import check_optional_dependency
from ..types.models.action import Action, ActionType
from .agent_wrappers import SocketIOActionHandler, SocketIOImageProvider
from .config import ServerConfig
from .models import (
    BaseActionEventData,
    ClickEventData,
    DragEventData,
    ErrorEventData,
    FinishEventData,
    HotkeyEventData,
    InitEventData,
    ScrollEventData,
    TypeEventData,
    WaitEventData,
)
from .session_store import Session, session_store

check_optional_dependency("socketio", "Server features", "server")
import socketio  # noqa: E402

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)


class SessionNamespace(socketio.AsyncNamespace):
    def __init__(self, namespace: str, config: ServerConfig):
        super().__init__(namespace)
        self.config = config
        self.background_tasks: dict[str, asyncio.Task] = {}

    async def on_connect(self, sid: str, environ: dict, auth: dict | None) -> bool:
        session_id = self.namespace.split("/")[-1]
        logger.info(f"Client {sid} connected to session {session_id}")

        session = session_store.get_session(session_id)
        if session:
            session.socket_id = sid
            session.namespace = self.namespace
            session_store.update_activity(session_id)

            # Create OAGI client if not exists
            if not session.oagi_client:
                session.oagi_client = AsyncClient(
                    base_url=self.config.oagi_base_url,
                    api_key=self.config.oagi_api_key,
                )
        else:
            logger.warning(f"Connection to non-existent session {session_id}")
            # Create session on connect if it doesn't exist
            session = Session(
                session_id=session_id,
                instruction="",
                mode="actor",  # Default mode
                model=self.config.default_model,
                temperature=self.config.default_temperature,
            )
            session.socket_id = sid
            session.namespace = self.namespace
            session.oagi_client = AsyncClient(
                base_url=self.config.oagi_base_url,
                api_key=self.config.oagi_api_key,
            )
            session_store.sessions[session_id] = session

        return True

    async def on_disconnect(self, sid: str) -> None:
        session_id = self.namespace.split("/")[-1]
        logger.info(f"Client {sid} disconnected from session {session_id}")

        # Cancel any background tasks
        if sid in self.background_tasks:
            self.background_tasks[sid].cancel()
            del self.background_tasks[sid]

        # Start cleanup task
        asyncio.create_task(self._cleanup_after_timeout(session_id))

    async def _cleanup_after_timeout(self, session_id: str) -> None:
        await asyncio.sleep(self.config.session_timeout_seconds)

        session = session_store.get_session(session_id)
        if session:
            current_time = datetime.now().timestamp()
            if (
                current_time - session.last_activity
                >= self.config.session_timeout_seconds
            ):
                logger.info(f"Session {session_id} timed out, cleaning up")

                # Close OAGI client
                if session.oagi_client:
                    await session.oagi_client.close()

                session_store.delete_session(session_id)

    async def on_init(self, sid: str, data: dict) -> None:
        try:
            session_id = self.namespace.split("/")[-1]
            logger.info(f"Initializing session {session_id}")

            # Validate input
            event_data = InitEventData(**data)

            # Get or create session
            session = session_store.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                await self.emit(
                    "error",
                    ErrorEventData(
                        message=f"Session {session_id} not found"
                    ).model_dump(),
                    room=sid,
                )
                return

            # Update session with init data
            session.instruction = event_data.instruction
            if event_data.mode:
                session.mode = event_data.mode
            if event_data.model:
                session.model = event_data.model
            if event_data.temperature is not None:
                session.temperature = event_data.temperature
            session.status = "running"
            session_store.update_activity(session_id)

            logger.info(
                f"Session {session_id} initialized with: {event_data.instruction} "
                f"(mode={event_data.mode}, model={event_data.model})"
            )

            # Create agent and wrappers
            agent = create_agent(
                mode=session.mode,
                api_key=self.config.oagi_api_key,
                base_url=self.config.oagi_base_url,
                max_steps=self.config.max_steps,
                model=event_data.model,
                temperature=event_data.temperature,
            )

            action_handler = SocketIOActionHandler(self, session)
            image_provider = SocketIOImageProvider(self, session, session.oagi_client)

            # Start execution in background using agent
            task = asyncio.create_task(
                self._run_agent_task(
                    agent,
                    session,
                    action_handler,
                    image_provider,
                    event_data.instruction,
                )
            )
            self.background_tasks[sid] = task

        except ValidationError as e:
            logger.error(f"Invalid init data: {e}")
            await self.emit(
                "error",
                ErrorEventData(
                    message="Invalid init data",
                    details={"validation_errors": e.errors()},
                ).model_dump(),
                room=sid,
            )
        except Exception as e:
            logger.error(f"Error in init: {e}", exc_info=True)
            await self.emit(
                "error",
                ErrorEventData(message=str(e)).model_dump(),
                room=sid,
            )

    async def _run_agent_task(
        self,
        agent: AsyncDefaultAgent,
        session: Session,
        action_handler: SocketIOActionHandler,
        image_provider: SocketIOImageProvider,
        instruction: str,
    ) -> None:
        try:
            # Execute task using agent
            success = await agent.execute(
                instruction=instruction,
                action_handler=action_handler,
                image_provider=image_provider,
            )

            # Update session status
            if success:
                session.status = "completed"
                logger.info(
                    f"Task completed successfully for session {session.session_id}"
                )

                # Emit finish event
                await self.call(
                    "finish",
                    FinishEventData(index=0, total=1).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )
            else:
                session.status = "failed"
                logger.warning(f"Task failed for session {session.session_id}")

            session_store.update_activity(session.session_id)

        except asyncio.CancelledError:
            logger.info(f"Agent task cancelled for session {session.session_id}")
            session.status = "cancelled"
        except Exception as e:
            logger.error(f"Error in agent task: {e}", exc_info=True)
            session.status = "failed"
            if session.socket_id:
                await self.emit(
                    "error",
                    ErrorEventData(message=f"Execution failed: {str(e)}").model_dump(),
                    room=session.socket_id,
                )

    async def _emit_actions(self, session: Session, actions: list[Action]) -> None:
        total = len(actions)

        for i, action in enumerate(actions):
            try:
                ack = await self._emit_single_action(session, action, i, total)
                session.actions_executed += 1

                if ack and not ack.get("success"):
                    logger.warning(f"Action {i} failed: {ack.get('error')}")

            except Exception as e:
                logger.error(f"Error emitting action {i}: {e}", exc_info=True)

    async def _emit_single_action(
        self, session: Session, action: Action, index: int, total: int
    ) -> dict | None:
        arg = action.argument.strip("()")
        common = BaseActionEventData(index=index, total=total).model_dump()

        logger.info(f"Emitting action {index + 1}/{total}: {action.type.value} {arg}")
        match action.type:
            case (
                ActionType.CLICK
                | ActionType.LEFT_DOUBLE
                | ActionType.LEFT_TRIPLE
                | ActionType.RIGHT_SINGLE
            ):
                coords = arg.split(",")
                if len(coords) >= 2:
                    x, y = int(coords[0]), int(coords[1])
                else:
                    logger.warning(f"Invalid action coordinates: {arg}")
                    return None

                return await self.call(
                    action.type.value,
                    ClickEventData(**common, x=x, y=y).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.DRAG:
                coords = arg.split(",")
                if len(coords) >= 4:
                    x1, y1, x2, y2 = (int(coords[i]) for i in range(4))
                else:
                    logger.warning(f"Invalid drag coordinates: {arg}")
                    return None

                return await self.call(
                    "drag",
                    DragEventData(**common, x1=x1, y1=y1, x2=x2, y2=y2).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.HOTKEY:
                combo = arg.strip()
                count = action.count or 1

                return await self.call(
                    "hotkey",
                    HotkeyEventData(**common, combo=combo, count=count).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.TYPE:
                text = arg.strip()

                return await self.call(
                    "type",
                    TypeEventData(**common, text=text).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.SCROLL:
                parts = arg.split(",")
                if len(parts) >= 3:
                    x, y = int(parts[0]), int(parts[1])
                    direction = parts[2].strip().lower()
                else:
                    logger.warning(f"Invalid scroll coordinates: {arg}")
                    return None

                count = action.count or 1

                return await self.call(
                    "scroll",
                    ScrollEventData(
                        **common,
                        x=x,
                        y=y,
                        direction=direction,
                        count=count,  # type: ignore
                    ).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.WAIT:
                try:
                    duration_ms = int(arg) if arg else 1000
                except (ValueError, TypeError):
                    duration_ms = 1000

                return await self.call(
                    "wait",
                    WaitEventData(**common, duration_ms=duration_ms).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.FINISH:
                return await self.call(
                    "finish",
                    FinishEventData(**common).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case _:
                logger.warning(f"Unknown action type: {action.type}")
                return None


# Dynamic namespace registration
_registered_namespaces: dict[str, SessionNamespace] = {}


def get_or_create_namespace(namespace: str, config: ServerConfig) -> SessionNamespace:
    if namespace not in _registered_namespaces:
        ns = SessionNamespace(namespace, config)
        sio.register_namespace(ns)
        _registered_namespaces[namespace] = ns
        logger.info(f"Registered namespace: {namespace}")
    return _registered_namespaces[namespace]


# Patch connect handler for dynamic registration
original_connect = sio._handle_connect


async def _patched_handle_connect(eio_sid: str, namespace: str, data: Any) -> Any:
    if namespace and namespace.startswith("/session/"):
        config = ServerConfig()
        get_or_create_namespace(namespace, config)
    return await original_connect(eio_sid, namespace, data)


sio._handle_connect = _patched_handle_connect

# Create ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path="socket.io")

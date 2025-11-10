"""Socket.IO server implementation."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import socketio
from pydantic import ValidationError

from ..client import AsyncClient
from ..types.models.action import Action, ActionType
from .config import ServerConfig
from .models import (
    ClickEventData,
    DragEventData,
    ErrorEventData,
    FinishEventData,
    HotkeyEventData,
    InitEventData,
    ScreenshotRequestData,
    ScreenshotResponseData,
    ScrollEventData,
    TypeEventData,
    WaitEventData,
)
from .session_store import Session, session_store

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
        self.background_tasks: Dict[str, asyncio.Task] = {}

    async def on_connect(self, sid: str, environ: dict, auth: Optional[dict]) -> bool:
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
            if event_data.model:
                session.model = event_data.model
            if event_data.temperature is not None:
                session.temperature = event_data.temperature
            session.status = "running"
            session_store.update_activity(session_id)

            logger.info(
                f"Session {session_id} initialized with: {event_data.instruction}"
            )

            # Start execution in background
            task = asyncio.create_task(self._run_execution_loop(session))
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

    async def _run_execution_loop(self, session: Session) -> None:
        try:
            while session.status == "running":
                success = await self._request_screenshot_and_process(session)

                if not success:
                    logger.warning(
                        f"Screenshot processing failed for session {session.session_id}"
                    )
                    break

                if session.status == "completed":
                    logger.info(f"Session {session.session_id} completed")
                    break

        except asyncio.CancelledError:
            logger.info(f"Execution loop cancelled for session {session.session_id}")
        except Exception as e:
            logger.error(f"Error in execution loop: {e}", exc_info=True)
            session.status = "failed"
            if session.socket_id:
                await self.emit(
                    "error",
                    ErrorEventData(message=f"Execution failed: {str(e)}").model_dump(),
                    room=session.socket_id,
                )

    async def _request_screenshot_and_process(self, session: Session) -> bool:
        try:
            if not session.oagi_client:
                logger.error(f"No OAGI client for session {session.session_id}")
                return False

            # Get S3 presigned URL
            upload_response = await session.oagi_client.get_s3_presigned_url()

            # Request screenshot from client
            screenshot_data = await self.call(
                "request_screenshot",
                ScreenshotRequestData(
                    presigned_url=upload_response.url,
                    uuid=upload_response.uuid,
                    expires_at=upload_response.expires_at,
                ).model_dump(),
                to=session.socket_id,
                timeout=self.config.socketio_timeout,
            )

            if not screenshot_data:
                logger.error("No response from screenshot request")
                return False

            # Validate response
            ack = ScreenshotResponseData(**screenshot_data)
            if not ack.success:
                logger.error(f"Screenshot upload failed: {ack.error}")
                await self.emit(
                    "error",
                    ErrorEventData(
                        message=f"Screenshot upload failed: {ack.error}"
                    ).model_dump(),
                    room=session.socket_id,
                )
                return False

            # Store screenshot URL
            session.current_screenshot_url = upload_response.download_url

            # Build message history with screenshot
            messages = session.message_history.copy()
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": upload_response.download_url},
                        }
                    ],
                }
            )

            # Call OAGI API
            response = await session.oagi_client.create_message(
                model=session.model,
                screenshot=b"",  # Empty bytes since already uploaded to S3
                task_description=session.instruction
                if not session.message_history
                else None,
                task_id=session.task_id,
                messages_history=messages,
                temperature=session.temperature,
            )

            # Update message history
            if response.raw_output:
                session.message_history.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": upload_response.download_url},
                            }
                        ],
                    }
                )
                session.message_history.append(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": response.raw_output}],
                    }
                )

            # Process and emit actions
            if response.actions:
                await self._emit_actions(session, response.actions)

            # Check if complete
            if response.is_complete:
                session.status = "completed"
                logger.info(f"Task completed for session {session.session_id}")
                await self.call(
                    "finish",
                    FinishEventData(action_index=0, total_actions=1).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            session_store.update_activity(session.session_id)
            return True

        except TimeoutError:
            logger.error(f"Screenshot timeout for session {session.session_id}")
            await self.emit(
                "error",
                ErrorEventData(message="Screenshot request timed out").model_dump(),
                room=session.socket_id,
            )
            return False
        except Exception as e:
            logger.error(f"Error processing screenshot: {e}", exc_info=True)
            await self.emit(
                "error",
                ErrorEventData(message=f"Processing error: {str(e)}").model_dump(),
                room=session.socket_id,
            )
            return False

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
    ) -> Optional[dict]:
        arg = action.argument.strip("()")
        common = {"action_index": index, "total_actions": total}

        match action.type:
            case ActionType.CLICK | ActionType.LEFT_DOUBLE | ActionType.RIGHT_SINGLE:
                coords = arg.split(",")
                x, y = (
                    int(coords[0]),
                    int(coords[1]) if len(coords) > 1 else (int(coords[0]), 500),
                )

                event_name = {
                    ActionType.CLICK: "click",
                    ActionType.LEFT_DOUBLE: "left_double",
                    ActionType.RIGHT_SINGLE: "right_single",
                }[action.type]

                click_type = {
                    ActionType.CLICK: "single",
                    ActionType.LEFT_DOUBLE: "double",
                    ActionType.RIGHT_SINGLE: "right",
                }[action.type]

                return await self.call(
                    event_name,
                    ClickEventData(
                        **common, x=x, y=y, click_type=click_type
                    ).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.DRAG:
                coords = arg.split(",")
                if len(coords) >= 4:
                    x1, y1, x2, y2 = (
                        int(coords[0]),
                        int(coords[1]),
                        int(coords[2]),
                        int(coords[3]),
                    )
                else:
                    x1, y1, x2, y2 = 100, 100, 200, 200

                return await self.call(
                    "drag",
                    DragEventData(**common, x1=x1, y1=y1, x2=x2, y2=y2).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.HOTKEY:
                combo = arg.strip("\"'")
                count = action.count or 1

                return await self.call(
                    "hotkey",
                    HotkeyEventData(**common, combo=combo, count=count).model_dump(),
                    to=session.socket_id,
                    timeout=self.config.socketio_timeout,
                )

            case ActionType.TYPE:
                text = arg.strip("\"'")

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
                elif len(parts) == 1:
                    x, y = 500, 500
                    direction = parts[0].strip().lower()
                else:
                    x, y = 500, 500
                    direction = "down"

                if direction not in ["up", "down", "left", "right"]:
                    direction = "down"

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
                return None

            case _:
                logger.warning(f"Unknown action type: {action.type}")
                return None


# Dynamic namespace registration
_registered_namespaces: Dict[str, SessionNamespace] = {}


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

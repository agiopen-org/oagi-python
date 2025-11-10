# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import logging
from typing import TYPE_CHECKING

from ..types import URLImage
from ..types.models.action import Action
from .models import ScreenshotRequestData, ScreenshotResponseData

if TYPE_CHECKING:
    from .session_store import Session
    from .socketio_server import SessionNamespace

logger = logging.getLogger(__name__)


class SocketIOActionHandler:
    """Wraps Socket.IO connection as an AsyncActionHandler.

    This handler emits actions through the Socket.IO connection to the client.
    """

    def __init__(self, namespace: "SessionNamespace", session: "Session"):
        self.namespace = namespace
        self.session = session

    async def __call__(self, actions: list[Action]) -> None:
        if not actions:
            logger.debug("No actions to execute")
            return

        logger.debug(f"Executing {len(actions)} actions via Socket.IO")
        await self.namespace._emit_actions(self.session, actions)


class SocketIOImageProvider:
    """Wraps Socket.IO connection as an AsyncImageProvider.

    This provider requests screenshots from the client through Socket.IO.
    """

    def __init__(
        self,
        namespace: "SessionNamespace",
        session: "Session",
        oagi_client,
    ):
        self.namespace = namespace
        self.session = session
        self.oagi_client = oagi_client
        self._last_url: str | None = None

    async def __call__(self) -> URLImage:
        logger.debug("Requesting screenshot via Socket.IO")

        # Get S3 presigned URL from OAGI
        upload_response = await self.oagi_client.get_s3_presigned_url()

        # Request screenshot from client with the presigned URL
        screenshot_data = await self.namespace.call(
            "request_screenshot",
            ScreenshotRequestData(
                presigned_url=upload_response.url,
                uuid=upload_response.uuid,
                expires_at=str(upload_response.expires_at),  # Convert int to string
            ).model_dump(),
            to=self.session.socket_id,
            timeout=self.namespace.config.socketio_timeout,
        )

        if not screenshot_data:
            raise Exception("No response from screenshot request")

        # Validate response
        ack = ScreenshotResponseData(**screenshot_data)
        if not ack.success:
            raise Exception(f"Screenshot upload failed: {ack.error}")

        # Store the URL for last_image()
        self._last_url = upload_response.download_url
        self.session.current_screenshot_url = upload_response.download_url

        logger.debug(f"Screenshot captured successfully: {upload_response.uuid}")
        return URLImage(upload_response.download_url)

    async def last_image(self) -> URLImage:
        if self._last_url:
            logger.debug("Returning last captured screenshot")
            return URLImage(self._last_url)

        logger.debug("No previous screenshot, capturing new one")
        return await self()

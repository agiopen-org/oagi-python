# -----------------------------------------------------------------------------
#  Copyright (c) OpenAGI Foundation
#  All rights reserved.
#
#  This file is part of the official API project.
#  Licensed under the MIT License.
# -----------------------------------------------------------------------------

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from oagi import ImageConfig, PyautoguiConfig
from oagi.handler.async_pyautogui_action_handler import AsyncPyautoguiActionHandler
from oagi.handler.async_screenshot_maker import AsyncScreenshotMaker
from oagi.handler.pil_image import PILImage
from oagi.types import Action, ActionType


@pytest.fixture
def mock_actions():
    return [
        Action(type=ActionType.CLICK, argument="500, 300", count=1),
        Action(type=ActionType.TYPE, argument="test", count=1),
    ]


@pytest.fixture
def mock_image():
    mock = Mock(spec=PILImage)
    mock.read.return_value = b"test-image-data"
    return mock


@pytest.fixture
def custom_pyautogui_config():
    return PyautoguiConfig(
        drag_duration=1.0,
        scroll_amount=50,
        wait_duration=2.0,
        action_pause=0.5,
    )


@pytest.fixture
def custom_image_config():
    return ImageConfig(
        format="PNG",
        quality=95,
        width=1920,
        height=1080,
    )


class TestAsyncPyautoguiActionHandler:
    @pytest.mark.asyncio
    async def test_init_with_default_config(self):
        handler = AsyncPyautoguiActionHandler()
        assert handler.sync_handler is not None
        assert isinstance(handler.config, PyautoguiConfig)

    @pytest.mark.asyncio
    async def test_init_with_custom_config(self, custom_pyautogui_config):
        handler = AsyncPyautoguiActionHandler(config=custom_pyautogui_config)
        assert handler.config == custom_pyautogui_config
        assert handler.sync_handler.config == custom_pyautogui_config

    @pytest.mark.asyncio
    async def test_execute_actions_with_thread_pool(self, mock_actions):
        handler = AsyncPyautoguiActionHandler()

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock()
            mock_get_loop.return_value = mock_loop

            await handler(mock_actions)
            mock_loop.run_in_executor.assert_called_once_with(
                None, handler.sync_handler, mock_actions
            )

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        handler = AsyncPyautoguiActionHandler()
        actions = [Action(type=ActionType.WAIT, argument="", count=1)]

        async def other_task():
            await asyncio.sleep(0.01)
            return "completed"

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock()
            mock_get_loop.return_value = mock_loop

            results = await asyncio.gather(
                handler(actions),
                other_task(),
            )
            mock_loop.run_in_executor.assert_called_once_with(
                None, handler.sync_handler, actions
            )
            assert results[1] == "completed"


class TestAsyncScreenshotMaker:
    @pytest.mark.asyncio
    async def test_init_with_default_config(self):
        maker = AsyncScreenshotMaker()
        assert maker.sync_screenshot_maker is not None
        assert maker.config is None

    @pytest.mark.asyncio
    async def test_init_with_custom_config(self, custom_image_config):
        maker = AsyncScreenshotMaker(config=custom_image_config)
        assert maker.config == custom_image_config
        assert maker.sync_screenshot_maker.config == custom_image_config

    @pytest.mark.asyncio
    async def test_capture_screenshot_with_thread_pool(self, mock_image):
        maker = AsyncScreenshotMaker()

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(return_value=mock_image)
            mock_get_loop.return_value = mock_loop

            result = await maker()
            mock_loop.run_in_executor.assert_called_once_with(
                None, maker.sync_screenshot_maker
            )
            assert result == mock_image

    @pytest.mark.asyncio
    async def test_concurrent_screenshot_capture(self):
        maker1 = AsyncScreenshotMaker()
        maker2 = AsyncScreenshotMaker()

        mock_image1 = Mock(spec=PILImage, id=1)
        mock_image2 = Mock(spec=PILImage, id=2)

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            # Set up different return values for each call
            mock_loop.run_in_executor.side_effect = [mock_image1, mock_image2]
            mock_get_loop.return_value = mock_loop

            results = await asyncio.gather(
                maker1(),
                maker2(),
            )

            assert mock_loop.run_in_executor.call_count == 2
            assert results[0].id == 1
            assert results[1].id == 2


class TestAsyncHandlerIntegration:
    @pytest.mark.asyncio
    async def test_handler_with_config_integration(
        self, mock_image, custom_pyautogui_config, custom_image_config
    ):
        handler = AsyncPyautoguiActionHandler(custom_pyautogui_config)
        maker = AsyncScreenshotMaker(custom_image_config)

        actions = [Action(type=ActionType.SCROLL, argument="500, 300, up", count=1)]

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(side_effect=[mock_image, None])
            mock_get_loop.return_value = mock_loop

            screenshot = await maker()
            await handler(actions)

            assert mock_loop.run_in_executor.call_count == 2
            mock_loop.run_in_executor.assert_any_call(None, maker.sync_screenshot_maker)
            mock_loop.run_in_executor.assert_any_call(
                None, handler.sync_handler, actions
            )
            assert screenshot == mock_image

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        handler = AsyncPyautoguiActionHandler()
        actions = [Action(type=ActionType.CLICK, argument="invalid", count=1)]

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock(
                side_effect=ValueError("Invalid coordinates")
            )
            mock_get_loop.return_value = mock_loop

            with pytest.raises(ValueError) as exc_info:
                await handler(actions)
            assert "Invalid coordinates" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_multiple_handlers_isolation(self, mock_actions):
        handler1 = AsyncPyautoguiActionHandler()
        handler2 = AsyncPyautoguiActionHandler()

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = AsyncMock()
            mock_loop.run_in_executor = AsyncMock()
            mock_get_loop.return_value = mock_loop

            await asyncio.gather(
                handler1(mock_actions),
                handler2(mock_actions),
            )

            assert mock_loop.run_in_executor.call_count == 2
            # Verify each handler called with its own sync_handler instance
            mock_loop.run_in_executor.assert_any_call(
                None, handler1.sync_handler, mock_actions
            )
            mock_loop.run_in_executor.assert_any_call(
                None, handler2.sync_handler, mock_actions
            )

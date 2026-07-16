from unittest.mock import AsyncMock

import pytest

from bot.services.generation_status import send_generation_status


@pytest.mark.asyncio
async def test_generation_status_sends_sticker_and_text_then_cleans_up():
    source = AsyncMock()
    sticker = AsyncMock()
    status = AsyncMock()
    source.answer_sticker.return_value = sticker
    source.answer.return_value = status

    generation_status = await send_generation_status(
        source,
        sticker_id="sticker-id",
        text="Generating...",
    )

    source.answer_sticker.assert_awaited_once_with("sticker-id")
    source.answer.assert_awaited_once_with("Generating...")

    await generation_status.complete()
    sticker.delete.assert_awaited_once()
    status.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_generation_status_falls_back_to_text_when_sticker_fails():
    source = AsyncMock()
    status = AsyncMock()
    source.answer_sticker.side_effect = RuntimeError("bad sticker")
    source.answer.return_value = status

    generation_status = await send_generation_status(
        source,
        sticker_id="bad-sticker",
        text="Generating...",
    )

    source.answer.assert_awaited_once_with("Generating...")
    await generation_status.fail("Failed")
    status.edit_text.assert_awaited_once_with("Failed")


@pytest.mark.asyncio
async def test_generation_status_without_sticker_only_sends_text():
    source = AsyncMock()
    source.answer.return_value = AsyncMock()

    await send_generation_status(source, sticker_id=None, text="Generating...")

    source.answer_sticker.assert_not_called()
    source.answer.assert_awaited_once_with("Generating...")

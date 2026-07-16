from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GenerationStatus:
    sticker_message: Any | None
    status_message: Any

    async def complete(self) -> None:
        await _delete_message(self.sticker_message)
        await _delete_message(self.status_message)

    async def fail(self, text: str) -> None:
        await _delete_message(self.sticker_message)
        try:
            await self.status_message.edit_text(text)
        except Exception:
            logger.exception("Failed to edit generation status message")


async def send_generation_status(
    target: Any,
    *,
    sticker_id: str | None,
    text: str,
) -> GenerationStatus:
    sticker_message = None
    if sticker_id:
        try:
            sticker_message = await target.answer_sticker(sticker_id)
        except Exception:
            logger.exception("Failed to send generation sticker")

    status_message = await target.answer(text)
    return GenerationStatus(sticker_message=sticker_message, status_message=status_message)


async def _delete_message(message: Any | None) -> None:
    if message is None:
        return
    try:
        await message.delete()
    except Exception:
        logger.exception("Failed to delete generation status message")

from aiogram.filters import Filter
from aiogram.types import Message

from bot.copy import active_copy


class TextIs(Filter):
    """Match reply-keyboard button text for the active locale."""

    def __init__(self, field: str) -> None:
        self.field = field

    async def __call__(self, message: Message) -> bool:
        if not message.text:
            return False
        expected = getattr(active_copy(), self.field, None)
        return message.text == expected

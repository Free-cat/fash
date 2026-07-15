import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Chat, Message, User
from bot.middleware import ActivityMiddleware


@pytest.mark.asyncio
async def test_activity_middleware_updates_and_cancels_drips(tmp_path):
    db = AsyncMock()
    drip = AsyncMock()
    middleware = ActivityMiddleware(db, drip)
    message = Message(
        message_id=1,
        date=0,
        chat=Chat(id=1, type="private"),
        from_user=User(id=42, is_bot=False, first_name="T"),
        text="hi",
    )
    handler = AsyncMock(return_value="ok")
    await middleware(handler, message, {})
    db.update_user_activity.assert_awaited_once_with(42)
    drip.cancel_all.assert_awaited_once_with(42)
    handler.assert_awaited_once()

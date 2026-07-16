import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.config import Settings
from bot.copy import active_copy, init_copy
from bot.db.database import Database
from bot.handlers.styleguide import (
    cancel_style_guide_offer,
    schedule_style_guide_offer,
    schedule_style_guide_offer_task,
)
from bot.keyboards import result_keyboard
from bot.services.openrouter import FileStorage
from bot.services.premium_offer import PREMIUM_OFFER_DELAY_SECONDS
from bot.services.proactive_guard import ProactiveGuard


def _test_settings(tmp_path: Path) -> Settings:
    preview = tmp_path / "premium_preview.jpg"
    preview.write_bytes(b"preview")
    return Settings(
        bot_token="token",
        openrouter_api_key="key",
        openrouter_model="model",
        openrouter_style_guide_model="sg-model",
        database_path=tmp_path / "bot.db",
        storage_path=tmp_path / "storage",
        free_credits=2,
        max_user_photos=5,
        locale="en",
        owner_telegram_id=None,
        webhook_url=None,
        webhook_secret=None,
        guide_photo_path=tmp_path / "guide.jpg",
        demo_image_path=tmp_path / "demo.jpg",
        premium_preview_path=preview,
        use_webhook=False,
    )


@pytest.mark.asyncio
async def test_record_generation_returns_id_and_style_guide_update(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=12345, username="test", free_credits=0)
    user_id = user["id"]
    gen_id = await db.record_generation(user_id, "/g.jpg", "/r.jpg")
    assert isinstance(gen_id, int)
    await db.set_style_guide_path(gen_id, user_id, "/sg.jpg")
    row = await db.get_generation(gen_id, user_id)
    assert row["style_guide_path"] == "/sg.jpg"
    assert row["style_guide_at"] is not None
    await db.close()


def test_result_keyboard_share_is_first_row():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.switch_inline_query is not None
    assert "styleguide" not in (first_btn.callback_data or "")


def test_result_keyboard_has_no_style_guide_button():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    callbacks = [
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert not any(c and c.startswith("styleguide:") for c in callbacks)


def test_premium_offer_copy_mentions_three_tryons():
    init_copy("en")
    copy = active_copy()
    assert "3" in copy.premium_offer_v1
    assert "3" in copy.btn_style_guide


def test_save_style_guide_photo(tmp_path):
    storage = FileStorage(tmp_path / "storage")
    path = storage.save_style_guide_photo(12345, 99, b"guide-bytes")
    assert path.name == "style_guide_99.jpg"
    assert path.read_bytes() == b"guide-bytes"


@pytest.mark.asyncio
async def test_schedule_style_guide_offer_skips_when_already_generated(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=999, username="test", free_credits=5)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")
    await db.set_style_guide_path(gen_id, user["id"], "/sg.jpg")
    guard = ProactiveGuard(db)
    settings = _test_settings(tmp_path)

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        await schedule_style_guide_offer(
            bot, db, guard, settings, 999, gen_id, balance=5
        )
    bot.send_message.assert_not_called()
    bot.send_photo.assert_not_called()
    await db.close()


@pytest.mark.asyncio
async def test_schedule_style_guide_offer_sends_cross_sell_when_low_balance(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=888, username="test", free_credits=0)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")
    guard = ProactiveGuard(db)
    settings = _test_settings(tmp_path)

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        await schedule_style_guide_offer(
            bot, db, guard, settings, 888, gen_id, balance=0
        )
    bot.send_message.assert_called_once()
    assert "3" in bot.send_message.call_args.args[1]
    await db.close()


@pytest.mark.asyncio
async def test_schedule_style_guide_offer_skips_when_generation_in_progress(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=777, username="test", free_credits=5)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")
    guard = ProactiveGuard(db)
    settings = _test_settings(tmp_path)

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        with patch(
            "bot.handlers.styleguide._style_guide_in_progress",
            {(777, gen_id)},
        ):
            await schedule_style_guide_offer(
                bot, db, guard, settings, 777, gen_id, balance=5
            )
    bot.send_message.assert_not_called()
    bot.send_photo.assert_not_called()
    await db.close()


@pytest.mark.asyncio
async def test_schedule_premium_offer_sends_ab_variant(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=555, username="test", free_credits=5)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")
    guard = MagicMock()
    guard.can_send = AsyncMock(return_value=True)
    settings = _test_settings(tmp_path)

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        await schedule_style_guide_offer(
            bot, db, guard, settings, 555, gen_id, balance=5
        )
    bot.send_photo.assert_called_once()
    caption = bot.send_photo.call_args.kwargs.get("caption", "")
    assert "stylist" in caption.lower() or "outfit" in caption.lower()
    await db.close()


@pytest.mark.asyncio
async def test_cancel_style_guide_offer_prevents_follow_up(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=666, username="test", free_credits=5)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")
    guard = ProactiveGuard(db)
    settings = _test_settings(tmp_path)

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        schedule_style_guide_offer_task(
            bot, db, guard, settings, 666, gen_id, balance=5
        )
        cancel_style_guide_offer(666, gen_id)
        await asyncio.sleep(0)

    bot.send_message.assert_not_called()
    bot.send_photo.assert_not_called()
    await db.close()


def test_premium_offer_delay_constant():
    assert PREMIUM_OFFER_DELAY_SECONDS == 12

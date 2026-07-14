import pytest
from unittest.mock import AsyncMock, patch

from bot.copy import active_copy, init_copy
from bot.db.database import Database
from bot.handlers.styleguide import STYLE_GUIDE_OFFER_DELAY_SECONDS, schedule_style_guide_offer
from bot.keyboards import result_keyboard
from bot.services.openrouter import FileStorage


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


def test_result_keyboard_style_guide_is_first_row():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.callback_data == "styleguide:42"
    assert "pair" in first_btn.text.lower()


def test_style_guide_copy_uses_try_on_not_credit():
    init_copy("en")
    copy = active_copy()
    assert "credit" not in copy.style_guide_offer.lower()
    assert "try-on" in copy.style_guide_offer.lower()


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

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        await schedule_style_guide_offer(bot, db, 999, gen_id, balance=5)
    bot.send_message.assert_not_called()
    await db.close()


@pytest.mark.asyncio
async def test_schedule_style_guide_offer_skips_when_no_balance(tmp_path):
    init_copy("en")
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(telegram_id=888, username="test", free_credits=0)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")

    bot = AsyncMock()
    with patch("bot.handlers.styleguide.asyncio.sleep", new_callable=AsyncMock):
        await schedule_style_guide_offer(bot, db, 888, gen_id, balance=0)
    bot.send_message.assert_not_called()
    await db.close()


def test_style_guide_offer_delay_constant():
    assert STYLE_GUIDE_OFFER_DELAY_SECONDS == 30

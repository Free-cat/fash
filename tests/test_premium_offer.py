import pytest
from bot.db.database import Database


@pytest.mark.asyncio
async def test_deduct_credits_requires_full_balance(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(1, "u", free_credits=2)
    assert await db.deduct_credits(1, 3) is False
    assert await db.get_balance(1) == 2


@pytest.mark.asyncio
async def test_deduct_credits_three_at_once(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(2, "u", free_credits=5)
    assert await db.deduct_credits(2, 3) is True
    assert await db.get_balance(2) == 2


@pytest.mark.asyncio
async def test_assign_premium_variant_once(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(3, "u", free_credits=0)
    await db.assign_premium_offer_variant(3, 2)
    state = await db.get_premium_offer_state(3)
    assert state["premium_offer_variant"] == 2
    await db.mark_premium_offer_shown(3)
    state = await db.get_premium_offer_state(3)
    assert state["premium_offer_shown_once"] == 1
    assert state["premium_offer_last_shown_at"] is not None


@pytest.mark.asyncio
async def test_increment_ignored_sets_pause_at_three(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(4, "u", free_credits=0)
    for _ in range(3):
        count = await db.increment_premium_offer_ignored(4)
    assert count == 3
    state = await db.get_premium_offer_state(4)
    assert state["premium_offer_paused_until"] is not None

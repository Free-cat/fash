import pytest
from bot.db.database import Database


def test_assign_variant_is_stable():
    from bot.services.premium_offer import assign_variant

    assert assign_variant(12345) == assign_variant(12345)
    assert assign_variant(12345) in (1, 2)


def test_consume_ignore_only_once():
    from bot.services.premium_offer import (
        clear_pending,
        consume_ignore_if_pending,
        register_pending,
    )

    register_pending(99, 1)
    assert consume_ignore_if_pending(99) is True
    assert consume_ignore_if_pending(99) is False
    clear_pending(99)
    register_pending(99, 2)
    assert consume_ignore_if_pending(99) is True


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
async def test_get_style_guide_cost_showcase_then_premium(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(5, "u", free_credits=0)
    assert await db.get_style_guide_cost(5) == 1
    assert await db.is_premium_showcase_available(5) is True
    await db.mark_premium_showcase_used(5)
    assert await db.get_style_guide_cost(5) == 3
    assert await db.is_premium_showcase_available(5) is False
    await db.close()


def test_style_guide_cost_helper():
    from bot.services.premium_offer import (
        PREMIUM_SHOWCASE_COST,
        PREMIUM_STYLE_GUIDE_COST,
        style_guide_cost,
    )

    assert PREMIUM_SHOWCASE_COST == 1
    assert style_guide_cost(showcase_available=True) == 1
    assert style_guide_cost(showcase_available=False) == PREMIUM_STYLE_GUIDE_COST


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
    await db.close()

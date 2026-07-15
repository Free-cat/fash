import pytest
from datetime import datetime, timedelta, timezone
from bot.db.database import Database
from bot.services.proactive_guard import ProactiveGuard, TOUCHPOINT_PREMIUM, TOUCHPOINT_DRIP


@pytest.mark.asyncio
async def test_blocks_when_generation_locked(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(10, "u", free_credits=0)
    await db.conn.execute(
        "INSERT INTO generation_locks (telegram_id, started_at) VALUES (10, datetime('now'))"
    )
    await db.conn.commit()
    guard = ProactiveGuard(db)
    assert await guard.can_send(10, TOUCHPOINT_PREMIUM) is False


@pytest.mark.asyncio
async def test_blocks_premium_when_recently_active(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(11, "u", free_credits=0)
    await db.update_user_activity(11)
    guard = ProactiveGuard(db)
    assert await guard.can_send(11, TOUCHPOINT_PREMIUM) is False


@pytest.mark.asyncio
async def test_blocks_premium_during_cooldown(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(12, "u", free_credits=0)
    await db.mark_premium_offer_shown(12)
    guard = ProactiveGuard(db)
    assert await guard.can_send(12, TOUCHPOINT_PREMIUM) is False


@pytest.mark.asyncio
async def test_blocks_premium_when_paused(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(13, "u", free_credits=0)
    future = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    await db.set_premium_offer_paused_until(13, future)
    guard = ProactiveGuard(db)
    assert await guard.can_send(13, TOUCHPOINT_PREMIUM) is False


@pytest.mark.asyncio
async def test_allows_drip_after_premium_activity_window(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(14, "u", free_credits=0)
    past = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    await db.conn.execute(
        "UPDATE users SET last_active_at = ? WHERE telegram_id = ?",
        (past.replace("T", " "), 14),
    )
    await db.conn.commit()
    guard = ProactiveGuard(db)
    assert await guard.can_send(14, TOUCHPOINT_DRIP) is True

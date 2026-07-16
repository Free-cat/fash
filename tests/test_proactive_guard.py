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
    await db.close()


@pytest.mark.asyncio
async def test_premium_allows_when_idle_since_schedule(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(11, "u", free_credits=0)
    past = (datetime.now(timezone.utc) - timedelta(seconds=30)).strftime("%Y-%m-%d %H:%M:%S")
    await db.conn.execute(
        "UPDATE users SET last_active_at = ? WHERE telegram_id = ?",
        (past, 11),
    )
    await db.conn.commit()
    idle_since = datetime.now(timezone.utc) - timedelta(seconds=12)
    guard = ProactiveGuard(db)
    assert await guard.can_send(11, TOUCHPOINT_PREMIUM, idle_since=idle_since) is True
    await db.close()


@pytest.mark.asyncio
async def test_premium_blocks_when_active_after_schedule(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(12, "u", free_credits=0)
    idle_since = datetime.now(timezone.utc) - timedelta(seconds=12)
    await db.update_user_activity(12)
    guard = ProactiveGuard(db)
    assert await guard.can_send(12, TOUCHPOINT_PREMIUM, idle_since=idle_since) is False
    await db.close()


@pytest.mark.asyncio
async def test_premium_allows_again_after_previous_offer(tmp_path):
    """No 4h cooldown — delayed can fire after every generation if idle."""
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(13, "u", free_credits=0)
    await db.mark_premium_offer_shown(13)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    await db.conn.execute(
        "UPDATE users SET last_active_at = ? WHERE telegram_id = ?",
        (past, 13),
    )
    await db.conn.commit()
    idle_since = datetime.now(timezone.utc) - timedelta(seconds=5)
    guard = ProactiveGuard(db)
    assert await guard.can_send(13, TOUCHPOINT_PREMIUM, idle_since=idle_since) is True
    await db.close()


@pytest.mark.asyncio
async def test_blocks_premium_when_paused(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(14, "u", free_credits=0)
    future = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    await db.set_premium_offer_paused_until(14, future)
    guard = ProactiveGuard(db)
    assert await guard.can_send(14, TOUCHPOINT_PREMIUM) is False
    await db.close()


@pytest.mark.asyncio
async def test_allows_drip_after_activity_window(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(15, "u", free_credits=0)
    past = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    await db.conn.execute(
        "UPDATE users SET last_active_at = ? WHERE telegram_id = ?",
        (past, 15),
    )
    await db.conn.commit()
    guard = ProactiveGuard(db)
    assert await guard.can_send(15, TOUCHPOINT_DRIP) is True
    await db.close()

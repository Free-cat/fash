import pytest

from bot.handlers.admin import _grant_credits


@pytest.mark.asyncio
async def test_admin_grant_credits_adds_balance(tmp_path):
    from bot.db.database import Database

    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(999, "user", free_credits=1)

    balance = await _grant_credits(db, target_id=999, amount=5)
    assert balance == 6

    cursor = await db.conn.execute(
        "SELECT event_name, payload FROM analytics_events WHERE telegram_id = 999"
    )
    row = await cursor.fetchone()
    assert row["event_name"] == "admin_grant"
    assert row["payload"] == "5"
    await db.close()


@pytest.mark.asyncio
async def test_admin_grant_creates_user_with_zero_balance(tmp_path):
    from bot.db.database import Database

    db = Database(tmp_path / "test.db")
    await db.connect()

    balance = await _grant_credits(db, target_id=12345, amount=3)
    assert balance == 3
    await db.close()

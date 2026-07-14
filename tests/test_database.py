import pytest
from bot.db.database import Database


@pytest.mark.asyncio
async def test_user_has_lifecycle_fields(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(123, "alice", free_credits=2)
    await db.update_user_activity(123)
    user = await db.fetch_user(123)
    assert user["last_active_at"] is not None
    assert user["drip_opt_out"] == 0
    assert user["total_purchases"] == 0
    await db.close()

import pytest

from bot.db.database import Database


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

import pytest
from bot.db.database import Database


@pytest.mark.asyncio
async def test_set_active_photo_only_one_active(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(111, None, 2))["id"]
    p1 = await db.add_user_photo(user_id, "/p1.jpg")
    p2 = await db.add_user_photo(user_id, "/p2.jpg")
    assert await db.set_active_photo(p1, user_id)
    active = await db.get_active_photo(user_id)
    assert active["id"] == p1
    assert await db.set_active_photo(p2, user_id)
    active = await db.get_active_photo(user_id)
    assert active["id"] == p2
    photos = await db.list_user_photos(user_id)
    assert sum(int(p["is_active"]) for p in photos) == 1


@pytest.mark.asyncio
async def test_look_cart_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(222, None, 2))["id"]
    await db.set_look_cart(user_id, ["/g1.jpg", "/g2.jpg"])
    assert await db.get_look_cart(user_id) == ["/g1.jpg", "/g2.jpg"]
    await db.clear_look_cart(user_id)
    assert await db.get_look_cart(user_id) == []

import pytest

from bot.db.database import Database


@pytest.mark.asyncio
async def test_active_look_and_waiting_add_item_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(101, "u", free_credits=2)
    gen_id = await db.record_generation(user["id"], "/g.jpg", "/r.jpg")

    await db.set_active_look(user["id"], gen_id)
    await db.set_waiting_look_add_item(user["id"], True)
    state = await db.get_active_look_state(user["id"])
    assert state["active_look_generation_id"] == gen_id
    assert state["waiting_look_add_item"] == 1

    await db.clear_look_completely(user["id"])
    state = await db.get_active_look_state(user["id"])
    assert state["active_look_generation_id"] is None
    assert state["waiting_look_add_item"] == 0
    assert await db.get_look_cart(user["id"]) == []
    await db.close()


@pytest.mark.asyncio
async def test_clear_look_also_clears_cart(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(102, "u", free_credits=2)
    await db.set_look_cart(user["id"], ["/a.jpg", "/b.jpg"])
    await db.set_active_look(user["id"], 9)
    await db.set_waiting_look_add_item(user["id"], True)

    await db.clear_look_completely(user["id"])
    assert await db.get_look_cart(user["id"]) == []
    state = await db.get_active_look_state(user["id"])
    assert state["active_look_generation_id"] is None
    assert state["waiting_look_add_item"] == 0
    await db.close()

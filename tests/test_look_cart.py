import io

import pytest
from PIL import Image

from bot.db.database import Database
from bot.services.look_cart import LookCartService
from bot.services.openrouter import FileStorage


def _make_garment_jpeg(width: int = 512, height: int = 512) -> bytes:
    image = Image.new("RGB", (width, height), color=(80, 160, 220))
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_add_garment_increments_cart(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(333, None, 2)
    storage = FileStorage(tmp_path / "storage")
    svc = LookCartService(db, storage)
    raw = _make_garment_jpeg()
    count, at_limit = await svc.add_garment(user["id"], 333, raw, generation_id=1)
    assert count == 1
    assert at_limit is False
    count2, _ = await svc.add_garment(user["id"], 333, raw, generation_id=2)
    assert count2 == 2


@pytest.mark.asyncio
async def test_add_garment_stops_at_five(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(444, None, 2)
    storage = FileStorage(tmp_path / "storage")
    svc = LookCartService(db, storage)
    raw = _make_garment_jpeg()

    for generation_id in range(1, 6):
        count, at_limit = await svc.add_garment(
            user["id"], 444, raw, generation_id=generation_id
        )
        assert count == generation_id
        assert at_limit == (generation_id == 5)

    count, at_limit = await svc.add_garment(user["id"], 444, raw, generation_id=6)
    assert count == 5
    assert at_limit is True
    assert len(await svc.paths(user["id"])) == 5


def test_look_cart_keyboard_has_generate():
    from bot.copy import init_copy
    from bot.keyboards import look_cart_keyboard

    init_copy("en")
    kb = look_cart_keyboard(2, at_limit=False)
    callbacks = [
        b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data
    ]
    assert "look:generate" in callbacks
    assert "look:clear" in callbacks


@pytest.mark.asyncio
async def test_record_generation_garment_count_and_mode(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(555, None, 2)
    gen_id = await db.record_generation(
        user["id"],
        "/g1.jpg,/g2.jpg",
        "/r.jpg",
        garment_count=2,
        mode="cart",
    )
    row = await db.get_generation(gen_id, user["id"])
    assert row["garment_count"] == 2
    assert row["mode"] == "cart"
    await db.close()


@pytest.mark.asyncio
async def test_purge_stale_look_carts(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(666, None, 2))["id"]
    await db.set_look_cart(user_id, ["/g.jpg"])
    await db.conn.execute(
        "UPDATE look_carts SET updated_at = datetime('now', '-25 hours') WHERE user_id = ?",
        (user_id,),
    )
    await db.conn.commit()
    removed = await db.purge_stale_look_carts(max_age_hours=24)
    assert removed == 1
    assert await db.get_look_cart(user_id) == []
    await db.close()

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

from datetime import datetime, timedelta, timezone

import pytest

from bot.db.database import Database
from bot.services.drip import DripService


@pytest.mark.asyncio
async def test_schedule_and_fetch_due_drip(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    drip = DripService(db)
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    await drip.schedule_at(100, "T2", past)
    due = await drip.fetch_due(limit=10)
    assert due[0]["drip_id"] == "T2"
    await db.close()


@pytest.mark.asyncio
async def test_cancel_all_drips(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    drip = DripService(db)
    await drip.schedule(200, "T1", delay_seconds=3600)
    await drip.cancel_all(200)
    due = await drip.fetch_due(limit=10)
    assert all(row["telegram_id"] != 200 for row in due)
    await db.close()


@pytest.mark.asyncio
async def test_schedule_delay(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    drip = DripService(db)
    await drip.schedule(300, "T1", delay_seconds=1800)
    due = await drip.fetch_due(limit=10)
    assert all(row["telegram_id"] != 300 for row in due)
    await db.close()

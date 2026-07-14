import pytest

from bot.db.database import Database
from bot.services.analytics import Analytics


@pytest.mark.asyncio
async def test_track_event(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    analytics = Analytics(db)
    await analytics.track(42, "user_registered")
    events = await analytics.list_events(42)
    assert events[0]["event_name"] == "user_registered"
    await db.close()

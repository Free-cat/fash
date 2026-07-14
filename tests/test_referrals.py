import pytest

from bot.db.database import Database
from bot.services.referrals import ReferralService, parse_start_payload


def test_parse_ref_payload():
    assert parse_start_payload("/start ref_12345") == 12345
    assert parse_start_payload("/start") is None


@pytest.mark.asyncio
async def test_referral_reward_after_first_tryon(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    ref = ReferralService(db)
    await db.get_or_create_user(1, "ref", 2)
    await db.get_or_create_user(2, "new", 2)
    await ref.attach_referral(referee_id=2, referrer_id=1)
    credited = await ref.on_first_tryon(2)
    assert credited is True
    assert await db.get_balance(1) == 3
    await db.close()

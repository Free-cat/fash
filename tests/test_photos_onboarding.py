import pytest

from bot.copy import init_copy
from bot.handlers.photos import _save_person_photo


@pytest.mark.asyncio
async def test_onboarding_completes_after_one_photo(tmp_path, monkeypatch):
    init_copy("en")

    from bot.config import Settings
    from bot.db.database import Database
    from bot.services.openrouter import FileStorage

    db = Database(tmp_path / "test.db")
    await db.connect()
    storage = FileStorage(tmp_path / "storage")
    settings = Settings(
        bot_token="x",
        openrouter_api_key="x",
        openrouter_model="google/gemini-3.1-flash-image",
        openrouter_style_guide_model="openai/gpt-image-2",
        database_path=tmp_path / "test.db",
        storage_path=tmp_path / "storage",
        free_credits=2,
        max_user_photos=3,
        locale="en",
        owner_telegram_id=None,
        webhook_url=None,
        webhook_secret=None,
        guide_photo_path=tmp_path / "guide.jpg",
        demo_image_path=tmp_path / "demo.jpg",
        premium_preview_path=tmp_path / "premium_preview.jpg",
        use_webhook=False,
    )

    answers: list[str] = []

    class FakeMessage:
        from_user = type("U", (), {"id": 42, "username": "alice"})()

        async def answer(self, text, **kwargs):
            answers.append(text)

    class FakeBot:
        async def get_file(self, file_id):
            return type("F", (), {"file_path": "photos/file.jpg"})()

        async def download_file(self, file_path):
            from io import BytesIO
            from PIL import Image

            buf = BytesIO()
            Image.new("RGB", (800, 1200), (100, 150, 200)).save(buf, "JPEG")
            return BytesIO(buf.getvalue())

    fake_photo = type("P", (), {"file_id": "abc"})()
    message = FakeMessage()
    message.photo = [fake_photo]

    await _save_person_photo(message, FakeBot(), db, settings, storage)

    user = await db.fetch_user(42)
    assert user["onboarding_complete"] == 1
    assert any("fitting room is ready" in a.lower() for a in answers)
    await db.close()

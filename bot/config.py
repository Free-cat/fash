import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from bot.services.openrouter import DEFAULT_STYLE_GUIDE_MODEL, DEFAULT_TRYON_MODEL

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_GENERATING_STICKER_ID = (
    "CAACAgQAAxkBAAERjX1qWVwwGE_33I-okc4In27JE9j5HgACKhEAAv9X8FH2t7Ww8CdM8D0E"
)


@dataclass(frozen=True)
class CreditPack:
    id: str
    credits: int
    stars: int
    label: str
    qty_label: str
    highlight: bool = False
    anchor_stars: int | None = None
    badge: str | None = None
    emoji: str = ""


def save_percent(pack: CreditPack) -> int | None:
    """Round % discount vs. buying `pack.credits` singles, or None if no anchor is set."""
    if not pack.anchor_stars:
        return None
    return round((1 - pack.stars / pack.anchor_stars) * 100)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    openrouter_api_key: str
    openrouter_model: str
    openrouter_style_guide_model: str
    database_path: Path
    storage_path: Path
    free_credits: int
    max_user_photos: int
    locale: str
    owner_telegram_id: int | None
    webhook_url: str | None
    webhook_secret: str | None
    guide_photo_path: Path
    demo_image_path: Path
    premium_preview_path: Path
    generating_sticker_id: str | None
    use_webhook: bool


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is required")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is required")

    owner_raw = os.getenv("OWNER_TELEGRAM_ID", "").strip()
    owner_telegram_id = int(owner_raw) if owner_raw else None

    return Settings(
        bot_token=bot_token,
        openrouter_api_key=openrouter_api_key,
        openrouter_model=os.getenv(
            "OPENROUTER_MODEL", DEFAULT_TRYON_MODEL
        ).strip(),
        openrouter_style_guide_model=os.getenv(
            "OPENROUTER_STYLE_GUIDE_MODEL", DEFAULT_STYLE_GUIDE_MODEL
        ).strip(),
        database_path=BASE_DIR / os.getenv("DATABASE_PATH", "data/bot.db"),
        storage_path=BASE_DIR / os.getenv("STORAGE_PATH", "data/storage"),
        free_credits=int(os.getenv("FREE_CREDITS", "2")),
        max_user_photos=int(os.getenv("MAX_USER_PHOTOS", "5")),
        locale=os.getenv("BOT_LOCALE", "en").strip().lower(),
        owner_telegram_id=owner_telegram_id,
        webhook_url=os.getenv("WEBHOOK_URL") or None,
        webhook_secret=os.getenv("WEBHOOK_SECRET") or None,
        guide_photo_path=BASE_DIR
        / os.getenv("GUIDE_PHOTO_PATH", "assets/guide/photo_guide.jpg"),
        demo_image_path=BASE_DIR
        / os.getenv("DEMO_IMAGE_PATH", "assets/demo/how_it_works.jpg"),
        premium_preview_path=BASE_DIR
        / os.getenv("PREMIUM_PREVIEW_PATH", "assets/guide/premium_preview.jpg"),
        generating_sticker_id=(
            os.getenv("GENERATING_STICKER_ID", DEFAULT_GENERATING_STICKER_ID).strip()
            or None
        ),
        use_webhook=os.getenv("USE_WEBHOOK", "false").lower() in ("1", "true", "yes"),
    )

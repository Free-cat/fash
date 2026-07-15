from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import Settings, load_settings
from bot.copy import init_copy
from bot.db.database import Database
from bot.handlers import admin, guide, look, payments, photos, privacy, referral, start, styleguide, tryon
from bot.middleware import AppMiddleware
from bot.services.drip import DripService
from bot.services.openrouter import FileStorage, OpenRouterClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/webhook"
WEBHOOK_HOST = "0.0.0.0"
WEBHOOK_PORT = 8080
PURGE_INTERVAL_SECONDS = 86_400


async def drip_worker(bot: Bot, drip: DripService) -> None:
    while True:
        try:
            await drip.process_due(bot)
        except Exception:
            logger.exception("Drip worker error")
        await asyncio.sleep(60)


async def purge_worker(db: Database, storage: FileStorage) -> None:
    while True:
        try:
            await privacy.purge_inactive_users(db, storage)
        except Exception:
            logger.exception("Purge worker error")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


async def look_cart_purge_worker(db: Database) -> None:
    while True:
        try:
            removed = await db.purge_stale_look_carts(max_age_hours=24)
            logger.info("Purged %d stale look cart(s)", removed)
        except Exception:
            logger.exception("Look cart purge worker error")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


def _register_routers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(guide.router)
    dp.include_router(photos.router)
    dp.include_router(payments.router)
    dp.include_router(referral.router)
    dp.include_router(look.router)
    dp.include_router(tryon.router)
    dp.include_router(styleguide.router)
    dp.include_router(privacy.router)
    dp.include_router(admin.router)


async def _cancel_workers(worker_tasks: list[asyncio.Task[None]]) -> None:
    for task in worker_tasks:
        task.cancel()
    for task in worker_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    logger.info("Starting polling mode")
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher, settings: Settings) -> None:
    if not settings.webhook_url:
        raise ValueError("WEBHOOK_URL is required when USE_WEBHOOK=true")

    webhook_url = f"{settings.webhook_url.rstrip('/')}{WEBHOOK_PATH}"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.webhook_secret,
    )

    app = web.Application()
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEBHOOK_HOST, WEBHOOK_PORT)
    await site.start()
    logger.info("Webhook server started on %s:%s (%s)", WEBHOOK_HOST, WEBHOOK_PORT, webhook_url)

    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()


async def main() -> None:
    settings = load_settings()
    copy = init_copy(settings.locale)
    db = Database(settings.database_path)
    await db.connect()

    storage = FileStorage(settings.storage_path)
    openrouter = OpenRouterClient(settings.openrouter_api_key, settings.openrouter_model)
    drip = DripService(db)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(
        AppMiddleware(
            db=db,
            settings=settings,
            storage=storage,
            openrouter=openrouter,
            drip=drip,
        )
    )

    _register_routers(dp)

    worker_tasks = [
        asyncio.create_task(drip_worker(bot, drip)),
        asyncio.create_task(purge_worker(db, storage)),
        asyncio.create_task(look_cart_purge_worker(db)),
    ]

    logger.info("Bot started (%s / locale=%s)", copy.brand_name, copy.locale)
    try:
        if settings.use_webhook:
            await _run_webhook(bot, dp, settings)
        else:
            await _run_polling(bot, dp)
    finally:
        await _cancel_workers(worker_tasks)
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

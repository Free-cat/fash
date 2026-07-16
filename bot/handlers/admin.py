from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import Settings
from bot.copy import active_copy
from bot.db.database import Database
from bot.services.analytics import Analytics
from bot.services.model_catalog import PAGE_SIZE, ModelCatalog, model_short_label
from bot.services.openrouter import OpenRouterClient

router = Router(name="admin")

TRYON_SETTING_KEY = "tryon_model"
STYLE_GUIDE_SETTING_KEY = "style_guide_model"
GRANT_AMOUNTS = (1, 3, 5, 10, 20)
MAX_GRANT_AMOUNT = 100


class AdminGrant(StatesGroup):
    waiting_user_id = State()


def _is_owner(user_id: int, settings: Settings) -> bool:
    return settings.owner_telegram_id is not None and user_id == settings.owner_telegram_id


def _admin_menu_text(tryon_model: str, style_guide_model: str) -> str:
    return (
        "⚙️ *Admin — generation models*\n\n"
        f"👗 Try-on: `{tryon_model}`\n"
        f"✨ Style guide: `{style_guide_model}`\n\n"
        "Changes apply to the whole bot immediately."
    )


def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👗 Try-on model",
                    callback_data="admin:pick:tryon:0",
                ),
                InlineKeyboardButton(
                    text="✨ Style guide model",
                    callback_data="admin:pick:style:0",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎁 Grant try-ons",
                    callback_data="admin:grant",
                ),
                InlineKeyboardButton(
                    text="📊 Stats",
                    callback_data="admin:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Refresh model list",
                    callback_data="admin:refresh",
                ),
            ],
        ]
    )


def _grant_amount_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"+{amount}",
                callback_data=f"admin:grant:{telegram_id}:{amount}",
            )
            for amount in GRANT_AMOUNTS[:3]
        ],
        [
            InlineKeyboardButton(
                text=f"+{amount}",
                callback_data=f"admin:grant:{telegram_id}:{amount}",
            )
            for amount in GRANT_AMOUNTS[3:]
        ],
        [InlineKeyboardButton(text="« Back", callback_data="admin:menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _model_picker_keyboard(
    *,
    kind: str,
    page: int,
    total_pages: int,
    models: list[str],
    active_model: str,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=model_short_label(model_id, active=model_id == active_model),
                callback_data=f"admin:set:{kind[0]}:{page}:{index}",
            )
        ]
        for index, model_id in enumerate(models)
    ]
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀ Prev",
                callback_data=f"admin:pick:{kind}:{page - 1}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}",
            callback_data="admin:noop",
        )
    )
    if page + 1 < total_pages:
        nav.append(
            InlineKeyboardButton(
                text="Next ▶",
                callback_data=f"admin:pick:{kind}:{page + 1}",
            )
        )
    rows.append(nav)
    rows.append(
        [InlineKeyboardButton(text="« Back", callback_data="admin:menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _grant_credits(
    db: Database,
    *,
    target_id: int,
    amount: int,
) -> int:
    if amount < 1 or amount > MAX_GRANT_AMOUNT:
        raise ValueError("invalid amount")
    await db.get_or_create_user(target_id, username=None, free_credits=0)
    await db.add_credits(target_id, amount)
    await Analytics(db).track(target_id, "admin_grant", str(amount))
    return await db.get_balance(target_id)


async def _show_admin_menu(
    *,
    message: Message | CallbackQuery,
    openrouter: OpenRouterClient,
    edit: bool,
) -> None:
    text = _admin_menu_text(openrouter.model, openrouter.style_guide_model)
    keyboard = _admin_menu_keyboard()
    if isinstance(message, CallbackQuery):
        if edit:
            await message.message.edit_text(
                text, parse_mode="Markdown", reply_markup=keyboard
            )
        else:
            await message.message.answer(
                text, parse_mode="Markdown", reply_markup=keyboard
            )
        await message.answer()
    else:
        await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.message(Command("admin"))
async def cmd_admin(
    message: Message,
    state: FSMContext,
    settings: Settings,
    openrouter: OpenRouterClient,
) -> None:
    if not _is_owner(message.from_user.id, settings):
        return
    await state.clear()
    await _show_admin_menu(message=message, openrouter=openrouter, edit=False)


@router.message(Command("cancel"))
async def cmd_cancel_admin(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_owner(message.from_user.id, settings):
        return
    current = await state.get_state()
    if current != AdminGrant.waiting_user_id.state:
        return
    await state.clear()
    await message.answer("Cancelled.")


@router.message(Command("grant"))
async def cmd_grant(
    message: Message,
    db: Database,
    settings: Settings,
) -> None:
    if not _is_owner(message.from_user.id, settings):
        return

    copy = active_copy()
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(
            "Usage: `/grant <telegram_id> <amount>`\n"
            "Example: `/grant 123456789 5`",
            parse_mode="Markdown",
        )
        return

    try:
        target_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer(copy.admin_grant_invalid_id)
        return

    try:
        balance = await _grant_credits(db, target_id=target_id, amount=amount)
    except ValueError:
        await message.answer(copy.admin_grant_amount_invalid)
        return

    await message.answer(
        copy.admin_grant_success.format(
            telegram_id=target_id,
            amount=amount,
            balance=balance,
        ),
        parse_mode="Markdown",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, settings: Settings) -> None:
    if not _is_owner(message.from_user.id, settings):
        return

    stats = await db.get_admin_stats()
    await message.answer(
        f"Users: {stats['users']}\n"
        f"Try-ons: {stats['generations']}\n"
        f"Purchases: {stats['purchases']}\n"
        f"Stars earned: {stats['stars']}\n"
        f"Conversion: {stats['conversion']:.1%}"
    )


@router.message(AdminGrant.waiting_user_id)
async def admin_grant_user_id(
    message: Message,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not _is_owner(message.from_user.id, settings):
        await state.clear()
        return

    copy = active_copy()
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(copy.admin_grant_invalid_id)
        return

    target_id = int(text)
    await db.get_or_create_user(target_id, username=None, free_credits=0)
    balance = await db.get_balance(target_id)
    await state.clear()
    await message.answer(
        copy.admin_grant_pick_amount.format(telegram_id=target_id, balance=balance),
        parse_mode="Markdown",
        reply_markup=_grant_amount_keyboard(target_id),
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callback(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
    openrouter: OpenRouterClient,
    model_catalog: ModelCatalog,
) -> None:
    if not _is_owner(callback.from_user.id, settings):
        await callback.answer()
        return

    parts = callback.data.split(":")
    action = parts[1]

    if action == "noop":
        await callback.answer()
        return

    if action == "menu":
        await state.clear()
        await _show_admin_menu(message=callback, openrouter=openrouter, edit=True)
        return

    if action == "grant":
        if len(parts) == 2:
            copy = active_copy()
            await state.set_state(AdminGrant.waiting_user_id)
            await callback.message.answer(
                copy.admin_grant_prompt_user,
                parse_mode="Markdown",
            )
            await callback.answer()
            return

        if len(parts) == 4:
            copy = active_copy()
            try:
                target_id = int(parts[2])
                amount = int(parts[3])
                balance = await _grant_credits(
                    db, target_id=target_id, amount=amount
                )
            except ValueError:
                await callback.answer(copy.admin_grant_amount_invalid, show_alert=True)
                return

            await callback.message.answer(
                copy.admin_grant_success.format(
                    telegram_id=target_id,
                    amount=amount,
                    balance=balance,
                ),
                parse_mode="Markdown",
            )
            await callback.answer(f"+{amount} granted")
            return

    if action == "refresh":
        try:
            await model_catalog.ensure_fresh(force=True)
            await callback.answer("Model list refreshed")
        except Exception as exc:
            await callback.answer(f"Refresh failed: {exc}", show_alert=True)
            return
        await _show_admin_menu(message=callback, openrouter=openrouter, edit=True)
        return

    if action == "stats":
        stats = await db.get_admin_stats()
        await callback.message.answer(
            f"Users: {stats['users']}\n"
            f"Try-ons: {stats['generations']}\n"
            f"Purchases: {stats['purchases']}\n"
            f"Stars earned: {stats['stars']}\n"
            f"Conversion: {stats['conversion']:.1%}"
        )
        await callback.answer()
        return

    if action == "pick":
        kind = parts[2]
        page = int(parts[3])
        try:
            await model_catalog.ensure_fresh()
        except Exception as exc:
            await callback.answer(f"Could not load models: {exc}", show_alert=True)
            return

        models, total_pages = model_catalog.page(kind, page)
        if not models:
            await callback.answer("No models found", show_alert=True)
            return

        active = (
            openrouter.model
            if kind == "tryon"
            else openrouter.style_guide_model
        )
        title = "👗 Try-on models" if kind == "tryon" else "✨ Style guide models"
        await callback.message.edit_text(
            f"{title}\nActive: `{active}`\nPick a model ({PAGE_SIZE} per page):",
            parse_mode="Markdown",
            reply_markup=_model_picker_keyboard(
                kind=kind,
                page=page,
                total_pages=total_pages,
                models=models,
                active_model=active,
            ),
        )
        await callback.answer()
        return

    if action == "set":
        kind_code = parts[2]
        page = int(parts[3])
        index = int(parts[4])
        kind = "tryon" if kind_code == "t" else "style"
        try:
            await model_catalog.ensure_fresh()
        except Exception as exc:
            await callback.answer(f"Could not load models: {exc}", show_alert=True)
            return

        models, total_pages = model_catalog.page(kind, page)
        if index >= len(models):
            await callback.answer("Model not found", show_alert=True)
            return

        model_id = models[index]
        if kind == "tryon":
            await db.set_bot_setting(TRYON_SETTING_KEY, model_id)
            openrouter.set_tryon_model(model_id)
        else:
            await db.set_bot_setting(STYLE_GUIDE_SETTING_KEY, model_id)
            openrouter.set_style_guide_model(model_id)

        await callback.answer(f"Set to {model_short_label(model_id)}")
        await _show_admin_menu(message=callback, openrouter=openrouter, edit=True)
        return

    await callback.answer()

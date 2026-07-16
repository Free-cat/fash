from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.config import CreditPack, save_percent
from bot.copy import active_copy
from bot.db.database import Database
from bot.filters import TextIs
from bot.keyboards import main_keyboard, shop_keyboard
from bot.services.analytics import Analytics
from bot.services.drip import DripService

router = Router(name="payments")


def _packs_by_id() -> dict[str, CreditPack]:
    return {pack.id: pack for pack in active_copy().credit_packs}


def _pack_payload(pack: CreditPack, telegram_id: int) -> str:
    return f"pack:{pack.id}:{telegram_id}"


def _parse_payload(payload: str) -> tuple[str, int] | None:
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "pack":
        return None
    try:
        return parts[1], int(parts[2])
    except ValueError:
        return None


def _pack_message_block(pack: CreditPack) -> list[str]:
    emoji = f"{pack.emoji} " if pack.emoji else ""
    title = f"{emoji}<b>{pack.label}</b>"
    if pack.badge:
        title += f" · {pack.badge}"

    pct = save_percent(pack)
    if pct:
        per_credit = round(pack.stars / pack.credits)
        price_line = f"<s>{pack.anchor_stars}⭐</s> → <b>{pack.stars}⭐</b>"
        save_line = f"<b>Save {pct}%</b> · {per_credit}⭐ each"
        return [title, price_line, save_line, ""]

    price_line = f"<b>{pack.stars}⭐</b>"
    return [title, price_line, ""]


async def _send_shop(message: Message, telegram_id: int, db: Database) -> None:
    copy = active_copy()
    lines = [copy.shop_header]
    if copy.shop_subheader:
        lines.append(copy.shop_subheader)
    lines.append("")

    for pack in copy.credit_packs:
        lines.extend(_pack_message_block(pack))

    await message.answer(
        "\n".join(lines).strip(),
        parse_mode="HTML",
        reply_markup=shop_keyboard(),
    )
    await Analytics(db).track(telegram_id, "shop_opened")


@router.message(Command("shop"))
@router.message(TextIs("btn_buy"))
async def cmd_shop(message: Message, db: Database) -> None:
    await _send_shop(message, message.from_user.id, db)


@router.callback_query(F.data == "shop:open")
async def open_shop(callback: CallbackQuery, db: Database) -> None:
    await _send_shop(callback.message, callback.from_user.id, db)
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_pack(callback: CallbackQuery) -> None:
    copy = active_copy()
    pack_id = callback.data.split(":", 1)[1]
    pack = _packs_by_id().get(pack_id)
    if not pack:
        await callback.answer("Unknown pack.", show_alert=True)
        return

    title = copy.invoice_credits_title.format(credits=pack.credits)
    description = copy.invoice_description
    pct = save_percent(pack)
    if pct and copy.invoice_discount_note:
        title = f"{title} (-{pct}%)"
        description = (
            copy.invoice_discount_note.format(
                anchor=pack.anchor_stars, stars=pack.stars, pct=pct
            )
            + description
        )

    await callback.message.answer_invoice(
        title=title,
        description=description,
        payload=_pack_payload(pack, callback.from_user.id),
        currency="XTR",
        prices=[LabeledPrice(label=pack.label, amount=pack.stars)],
        provider_token="",
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    parsed = _parse_payload(query.invoice_payload)
    if not parsed:
        await query.answer(ok=False, error_message="Invalid payment payload.")
        return

    pack_id, telegram_id = parsed
    if telegram_id != query.from_user.id:
        await query.answer(ok=False, error_message="Payment user mismatch.")
        return

    if pack_id not in _packs_by_id():
        await query.answer(ok=False, error_message="Unknown credit pack.")
        return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message, db: Database, drip: DripService
) -> None:
    copy = active_copy()
    payment = message.successful_payment
    parsed = _parse_payload(payment.invoice_payload)
    if not parsed:
        await message.answer("Payment received but payload is invalid. Contact support.")
        return

    pack_id, telegram_id = parsed
    if telegram_id != message.from_user.id:
        await message.answer("Payment user mismatch.")
        return

    pack = _packs_by_id().get(pack_id)
    if not pack:
        await message.answer("Unknown credit pack.")
        return

    if payment.currency != "XTR" or payment.total_amount != pack.stars:
        await message.answer("Payment amount mismatch.")
        return

    inserted = await db.record_payment(
        telegram_id=message.from_user.id,
        charge_id=payment.telegram_payment_charge_id,
        stars=payment.total_amount,
        credits=pack.credits,
        pack_id=pack.id,
    )
    if not inserted:
        balance = await db.get_balance(message.from_user.id)
        await message.answer(
            copy.payment_duplicate.format(balance=balance),
            reply_markup=main_keyboard(),
        )
        return

    await db.add_credits(message.from_user.id, pack.credits)
    await db.increment_total_purchases(message.from_user.id)
    await drip.cancel_all(message.from_user.id)

    analytics = Analytics(db)
    await analytics.track(message.from_user.id, "purchase", pack.id)

    if pack.id == "starter":
        await drip.schedule(
            message.from_user.id,
            "post_purchase_upsell",
            delay_seconds=30,
        )

    balance = await db.get_balance(message.from_user.id)
    await message.answer(
        copy.payment_success.format(credits=pack.credits, balance=balance),
        reply_markup=main_keyboard(),
    )

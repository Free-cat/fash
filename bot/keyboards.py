from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.config import CreditPack, save_percent
from bot.copy import active_copy


def main_keyboard() -> ReplyKeyboardMarkup:
    copy = active_copy()
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=copy.btn_try_on),
                KeyboardButton(text=copy.btn_balance),
            ],
            [
                KeyboardButton(text=copy.btn_buy),
                KeyboardButton(text=copy.btn_my_photos),
            ],
            [KeyboardButton(text=copy.btn_help)],
        ],
        resize_keyboard=True,
    )


def welcome_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy.btn_photo_guide,
                    callback_data="guide:show",
                )
            ],
        ],
    )


def guide_button_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy.btn_photo_guide,
                    callback_data="guide:show",
                )
            ],
        ],
    )


def pack_button_text(pack: CreditPack) -> str:
    """Short, scannable button label: emoji + quantity + price + discount."""
    emoji = f"{pack.emoji} " if pack.emoji else ""
    price = f"{pack.stars}⭐"
    pct = save_percent(pack)
    if pct:
        price += f" (-{pct}%)"
    return f"{emoji}{pack.qty_label} — {price}"


def shop_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [
        [
            InlineKeyboardButton(
                text=pack_button_text(pack),
                callback_data=f"buy:{pack.id}",
            )
        ]
        for pack in copy.credit_packs
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _style_guide_button(generation_id: int, cost: int) -> InlineKeyboardButton:
    copy = active_copy()
    text = copy.btn_style_guide_showcase if cost == 1 else copy.btn_style_guide
    return InlineKeyboardButton(
        text=text,
        callback_data=f"styleguide:{generation_id}",
    )


def result_keyboard(
    balance: int,
    generation_id: int,
    *,
    cost: int | None = None,
) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows: list[list[InlineKeyboardButton]] = []
    if (
        cost is not None
        and generation_id > 0
        and balance >= cost
    ):
        rows.append([_style_guide_button(generation_id, cost)])
    if generation_id > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_add_to_look,
                    callback_data=f"look:add_item:{generation_id}",
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_clear_look,
                    callback_data="look:clear",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=copy.btn_try_another,
                callback_data="action:try_another",
            ),
        ]
    )
    if balance <= 2:
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_buy_credits,
                    callback_data="shop:open",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def waiting_add_item_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy.btn_clear_look,
                    callback_data="look:clear",
                )
            ]
        ]
    )


def paywall_keyboard(
    *,
    generation_id: int = 0,
    cost: int | None = None,
) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows: list[list[InlineKeyboardButton]] = []
    # Full styling only when caller passes cost AND we are not in a zero-balance
    # upsell path. Call sites that show packs after insufficient balance must pass
    # cost=None.
    if cost is not None and generation_id > 0:
        rows.append([_style_guide_button(generation_id, cost)])
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=pack_button_text(pack),
                    callback_data=f"buy:{pack.id}",
                )
            ]
            for pack in copy.credit_packs
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=copy.btn_invite,
                callback_data="action:invite",
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deficit_keyboard(
    *,
    generation_id: int = 0,
    cost: int | None = None,
) -> InlineKeyboardMarkup:
    copy = active_copy()
    starter = next(p for p in copy.credit_packs if p.id == "starter")
    rows: list[list[InlineKeyboardButton]] = []
    if cost is not None and generation_id > 0:
        rows.append([_style_guide_button(generation_id, cost)])
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=pack_button_text(starter),
                    callback_data="buy:starter",
                )
            ],
            [
                InlineKeyboardButton(
                    text=copy.btn_buy_credits,
                    callback_data="shop:open",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def look_cart_keyboard(count: int, *, at_limit: bool) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [
        [
            InlineKeyboardButton(
                text=copy.btn_see_on_me,
                callback_data="look:generate",
            )
        ]
    ]
    if not at_limit:
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_add_item,
                    callback_data="look:add_hint",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text=copy.btn_clear_look,
                callback_data="look:clear",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def draft_look_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy.btn_see_on_me,
                    callback_data="look:generate",
                ),
                InlineKeyboardButton(
                    text=copy.btn_add_item,
                    callback_data="look:add_hint",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=copy.btn_clear_look,
                    callback_data="look:clear",
                )
            ],
        ]
    )


def style_guide_offer_keyboard(generation_id: int, *, cost: int) -> InlineKeyboardMarkup:
    copy = active_copy()
    button_text = copy.btn_style_guide_showcase if cost == 1 else copy.btn_style_guide
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"styleguide:{generation_id}",
                ),
            ],
        ],
    )

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

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
                KeyboardButton(text=copy.btn_reupload),
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


def shop_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = []
    for pack in copy.credit_packs:
        label = pack.label
        if pack.highlight:
            label = f"⭐ {label} — {copy.shop_most_chosen}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{label} — {pack.stars} ⭐",
                    callback_data=f"buy:{pack.id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deficit_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    starter = next(p for p in copy.credit_packs if p.id == "starter")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{starter.label} — {starter.stars} ⭐",
                    callback_data="buy:starter",
                )
            ],
            [
                InlineKeyboardButton(
                    text=copy.btn_buy_credits,
                    callback_data="shop:open",
                )
            ],
        ],
    )


def result_keyboard(balance: int, generation_id: int) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [
        [
            InlineKeyboardButton(
                text=copy.btn_style_guide,
                callback_data=f"styleguide:{generation_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text=copy.btn_try_another,
                callback_data="action:try_another",
            ),
            InlineKeyboardButton(
                text=copy.btn_invite,
                callback_data="action:invite",
            ),
        ],
        [
            InlineKeyboardButton(
                text=copy.btn_share,
                switch_inline_query=copy.share_inline_query,
            ),
        ],
    ]
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


def style_guide_offer_keyboard(generation_id: int) -> InlineKeyboardMarkup:
    copy = active_copy()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=copy.btn_style_guide,
                    callback_data=f"styleguide:{generation_id}",
                ),
            ],
        ],
    )

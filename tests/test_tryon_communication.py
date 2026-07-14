from aiogram.types import InlineKeyboardMarkup

from bot.copy import init_copy
from bot.handlers.tryon import build_result_message


def test_result_message_merges_low_balance_into_caption():
    init_copy("en")

    caption, keyboard = build_result_message(remaining=1, total_purchases=0)

    assert "This is *you* in that outfit 🔥" in caption
    assert "1 try-on(s) left — make them count" in caption
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert len(keyboard.inline_keyboard) == 3


def test_result_message_paywall_uses_shop_keyboard():
    init_copy("en")

    caption, keyboard = build_result_message(remaining=0, total_purchases=0)

    assert "That's your last free try-on" in caption
    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]
    assert callbacks and callbacks[0].startswith("buy:")

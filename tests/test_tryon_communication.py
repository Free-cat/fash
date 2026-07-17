from aiogram.types import InlineKeyboardMarkup

from bot.copy import init_copy
from bot.handlers.tryon import build_result_message


def test_result_message_merges_low_balance_into_caption():
    init_copy("en")

    caption, keyboard = build_result_message(
        remaining=1, total_purchases=0, generation_id=1, cost=1
    )

    assert "This is *you* in that outfit 🔥" in caption
    assert "1 try-on(s) left — make them count" in caption
    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert keyboard.inline_keyboard[0][0].callback_data == "styleguide:1"
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert "look:add_item:1" in callbacks
    assert "look:clear" in callbacks
    assert "action:try_another" in callbacks


def test_paywall_uses_paywall_keyboard_with_invite():
    init_copy("ru")

    caption, keyboard = build_result_message(
        remaining=0, total_purchases=0, generation_id=7, cost=3
    )

    assert "огонь" in caption
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert not any(c and c.startswith("styleguide:") for c in callbacks)
    assert any(c.startswith("buy:") for c in callbacks)
    assert "action:invite" in callbacks


def test_result_hides_style_guide_when_balance_below_cost():
    init_copy("en")

    caption, keyboard = build_result_message(
        remaining=1, total_purchases=0, generation_id=9, cost=3
    )

    assert "1 try-on(s) left" in caption
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert not any(c and c.startswith("styleguide:") for c in callbacks)
    assert "look:add_item:9" in callbacks
    assert "action:try_another" in callbacks

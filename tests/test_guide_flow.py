from bot.copy import init_copy
from bot.handlers.guide import guide_next_step


def test_guide_leads_new_user_to_person_photo():
    init_copy("en")

    text, keyboard = guide_next_step(onboarding_complete=False, balance=2)

    button = keyboard.inline_keyboard[0][0]
    assert text == "Great — now send your full-body photo here 📷"
    assert button.text == "📷 Upload my photo"
    assert button.callback_data == "guide:next:person"


def test_guide_leads_ready_user_to_garment_photo():
    init_copy("en")

    text, keyboard = guide_next_step(onboarding_complete=True, balance=2)

    button = keyboard.inline_keyboard[0][0]
    assert text == "Ready! Now send a clothing photo to see it on you 👗"
    assert button.text == "👗 Choose an outfit"
    assert button.callback_data == "guide:next:garment"

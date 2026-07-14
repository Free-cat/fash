from __future__ import annotations

from dataclasses import dataclass

from bot.config import CreditPack


@dataclass(frozen=True)
class Copy:
    locale: str
    brand_name: str
    tagline: str

    welcome_new: str
    welcome_back: str
    demo_caption: str
    photo_ready: str
    generating: str
    result_caption: str
    paywall: str
    deficit: str
    privacy_note: str
    drip_opt_out: str
    guide_caption: str
    guide_text_fallback: str
    guide_next_person: str
    guide_next_garment: str
    try_another: str
    low_balance: str
    invite_text: str
    share_inline_query: str

    btn_try_on: str
    btn_balance: str
    btn_buy: str
    btn_reupload: str
    btn_help: str
    btn_photo_guide: str
    btn_upload_person: str
    btn_choose_outfit: str
    btn_try_another: str
    btn_invite: str
    btn_share: str
    btn_buy_credits: str
    btn_style_guide: str

    style_guide_offer: str
    style_guide_generating: str
    style_guide_caption: str
    style_guide_already: str
    style_guide_failed: str
    style_guide_not_found: str
    shop_most_chosen: str

    help_text: str
    balance_text: str
    balance_line: str
    try_on_hint: str
    circuit_open: str
    concurrent: str
    not_enough_credits: str
    generation_failed: str
    photo_too_small: str
    photo_bad_format: str
    garment_too_small: str
    send_start_first: str
    upload_photos_first: str
    no_saved_photos: str
    photo_limit_reached: str
    photo_saved_send_garment: str
    photo_progress_optional: str
    reupload_prompt: str
    delete_confirmation: str
    stop_reminders: str
    stop_reminders_done: str

    shop_header: str
    shop_credit_line: str
    invoice_description: str
    invoice_credits_title: str
    payment_success: str
    payment_duplicate: str

    credit_packs: tuple[CreditPack, ...]
    drip_messages: dict[str, str]

    referral_returning: str


_active: Copy | None = None


def get_copy(locale: str) -> Copy:
    if locale == "ru":
        from bot.copy import ru

        return ru.COPY
    from bot.copy import en

    return en.COPY


def init_copy(locale: str) -> Copy:
    global _active
    _active = get_copy(locale)
    return _active


def active_copy() -> Copy:
    if _active is None:
        return get_copy("en")
    return _active

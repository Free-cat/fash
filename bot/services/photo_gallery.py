from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.copy import active_copy

NUMBERS_PER_PAGE = 5


def photo_index(photos: list, photo_id: int) -> int:
    for index, photo in enumerate(photos):
        if photo["id"] == photo_id:
            return index
    return 0


def photo_by_index(photos: list, index: int) -> dict:
    return photos[index % len(photos)]


def num_page_for_index(index: int) -> int:
    return index // NUMBERS_PER_PAGE


def num_page_count(photo_count: int) -> int:
    if photo_count == 0:
        return 1
    return (photo_count + NUMBERS_PER_PAGE - 1) // NUMBERS_PER_PAGE


def gallery_caption(photos: list, view_photo: dict, active_photo: dict | None) -> str:
    copy = active_copy()
    active_slot = active_photo["slot_index"] if active_photo else view_photo["slot_index"]
    return copy.gallery_header.format(
        count=len(photos),
        preview_slot=view_photo["slot_index"],
        active_slot=active_slot,
    )


def _number_label(*, slot: int, is_view: bool, is_active: bool) -> str:
    if is_active and is_view:
        return f"✓{slot}"
    if is_active:
        return f"{slot}✓"
    if is_view:
        return f"▸{slot}"
    return str(slot)


def photo_gallery_keyboard(
    photos: list,
    view_photo_id: int,
    num_page: int,
) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows: list[list[InlineKeyboardButton]] = []
    view_index = photo_index(photos, view_photo_id)
    view_photo = photos[view_index]
    active_photo = next((photo for photo in photos if photo["is_active"]), None)
    is_view_active = active_photo is not None and active_photo["id"] == view_photo_id

    if len(photos) > 1:
        position = f"{view_index + 1} / {len(photos)}"
        rows.append(
            [
                InlineKeyboardButton(
                    text="◀ Prev",
                    callback_data=f"photo:prev:{view_photo_id}",
                ),
                InlineKeyboardButton(
                    text=position,
                    callback_data="photo:noop",
                ),
                InlineKeyboardButton(
                    text="Next ▶",
                    callback_data=f"photo:next:{view_photo_id}",
                ),
            ]
        )

    total_num_pages = num_page_count(len(photos))
    num_page = max(0, min(num_page, total_num_pages - 1))
    start = num_page * NUMBERS_PER_PAGE
    number_row: list[InlineKeyboardButton] = []
    for photo in photos[start : start + NUMBERS_PER_PAGE]:
        slot = photo["slot_index"]
        is_view = photo["id"] == view_photo_id
        is_active = bool(photo["is_active"])
        number_row.append(
            InlineKeyboardButton(
                text=_number_label(slot=slot, is_view=is_view, is_active=is_active),
                callback_data=f"photo:view:{photo['id']}",
            )
        )
    if number_row:
        rows.append(number_row)

    if total_num_pages > 1:
        nav: list[InlineKeyboardButton] = []
        if num_page > 0:
            nav.append(
                InlineKeyboardButton(
                    text="◀",
                    callback_data=f"photo:npg:{num_page - 1}:{view_photo_id}",
                )
            )
        nav.append(
            InlineKeyboardButton(
                text=f"{num_page + 1}/{total_num_pages}",
                callback_data="photo:noop",
            )
        )
        if num_page + 1 < total_num_pages:
            nav.append(
                InlineKeyboardButton(
                    text="▶",
                    callback_data=f"photo:npg:{num_page + 1}:{view_photo_id}",
                )
            )
        rows.append(nav)

    if is_view_active:
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_photo_active,
                    callback_data="photo:noop",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text=copy.btn_use_photo,
                    callback_data=f"photo:use:{view_photo_id}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ Add photo",
                callback_data="photo:add",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def empty_gallery_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Add photo",
                    callback_data="photo:add",
                )
            ]
        ]
    )

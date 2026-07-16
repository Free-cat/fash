from bot.copy import init_copy
from bot.services.photo_gallery import (
    NUMBERS_PER_PAGE,
    gallery_caption,
    num_page_count,
    num_page_for_index,
    photo_by_index,
    photo_gallery_keyboard,
    photo_index,
)


def _make_photos(count: int, *, active_id: int = 1) -> list[dict]:
    return [
        {
            "id": index + 1,
            "slot_index": index + 1,
            "is_active": 1 if index + 1 == active_id else 0,
            "path": f"/p{index + 1}.jpg",
        }
        for index in range(count)
    ]


def test_gallery_caption_shows_preview_and_active():
    init_copy("en")
    photos = _make_photos(3, active_id=2)
    text = gallery_caption(photos, photos[1], photos[1])
    assert "Preview: Photo 2" in text
    assert "Active: Photo 2" in text


def test_number_labels_mark_view_and_active():
    photos = _make_photos(3, active_id=2)
    keyboard = photo_gallery_keyboard(photos, view_photo_id=1, num_page=0)
    labels = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "▸1" in labels
    assert "2✓" in labels


def test_pagination_shows_five_numbers_per_page():
    photos = _make_photos(8, active_id=1)
    keyboard = photo_gallery_keyboard(photos, view_photo_id=1, num_page=0)
    number_row = keyboard.inline_keyboard[1]
    assert len(number_row) == NUMBERS_PER_PAGE


def test_num_page_for_index():
    assert num_page_for_index(0) == 0
    assert num_page_for_index(5) == 1
    assert num_page_count(8) == 2


def test_prev_next_wrap_indices():
    photos = _make_photos(3)
    assert photo_by_index(photos, -1)["id"] == 3
    assert photo_by_index(photos, 3)["id"] == 1

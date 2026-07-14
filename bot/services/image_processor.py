from __future__ import annotations

import io

from PIL import Image, ImageOps

from bot.copy import active_copy

MAX_DIMENSION = 1024
GARMENT_MAX_DIMENSION = 768
JPEG_QUALITY = 90
MIN_DIMENSION = 256
PORTRAIT_RATIO = 3 / 4  # width / height
PAD_COLOR = (245, 240, 235)  # soft cream, matches brand accent


class PhotoValidationError(ValueError):
    pass


def _load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        image = ImageOps.exif_transpose(image)
        return image.convert("RGB")
    except Exception as exc:
        raise PhotoValidationError(active_copy().photo_bad_format) from exc


def validate_and_process_person_photo(data: bytes) -> bytes:
    image = _load_image(data)
    width, height = image.size

    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise PhotoValidationError(active_copy().photo_too_small)

    image = _fit_full_body_portrait(image, max_dim=MAX_DIMENSION)
    return _to_jpeg_bytes(image)


def validate_and_process_garment_photo(data: bytes) -> bytes:
    image = _load_image(data)
    width, height = image.size

    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise PhotoValidationError(active_copy().garment_too_small)

    image = _fit_contain(image, max_dim=GARMENT_MAX_DIMENSION)
    return _to_jpeg_bytes(image)


def _fit_full_body_portrait(image: Image.Image, max_dim: int) -> Image.Image:
    """Keep the entire person visible. Never crop head/feet — pad to 3:4 instead."""
    image = _fit_contain(image, max_dim=max_dim)
    width, height = image.size
    target_ratio = PORTRAIT_RATIO
    current_ratio = width / height

    if abs(current_ratio - target_ratio) < 0.02:
        return image

    if current_ratio > target_ratio:
        # Too wide → pad top/bottom (never crop sides of a person unnecessarily;
        # but for try-on, pad height to reach 3:4).
        new_height = int(round(width / target_ratio))
        canvas = Image.new("RGB", (width, new_height), PAD_COLOR)
        top = (new_height - height) // 2
        canvas.paste(image, (0, top))
        return canvas

    # Too tall / narrow → pad left/right, keep full height (head-to-toe).
    new_width = int(round(height * target_ratio))
    canvas = Image.new("RGB", (new_width, height), PAD_COLOR)
    left = (new_width - width) // 2
    canvas.paste(image, (left, 0))
    return canvas


def _fit_contain(image: Image.Image, max_dim: int) -> Image.Image:
    """Resize so both sides fit within max_dim. No cropping."""
    image = image.copy()
    image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return image


def _to_jpeg_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()

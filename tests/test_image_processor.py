from bot.services.image_processor import validate_and_process_person_photo
from PIL import Image
import io


def _make_full_body_jpeg(width: int = 1200, height: int = 2400) -> bytes:
    image = Image.new("RGB", (width, height), color=(40, 120, 200))
    # Mark head (top) and feet (bottom) with unique colors so crop can be verified.
    for y in range(0, 80):
        for x in range(width):
            image.putpixel((x, y), (255, 0, 0))  # head band
    for y in range(height - 80, height):
        for x in range(width):
            image.putpixel((x, y), (0, 255, 0))  # feet band
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_person_photo_keeps_head_and_feet():
    raw = _make_full_body_jpeg()
    processed = validate_and_process_person_photo(raw)
    result = Image.open(io.BytesIO(processed)).convert("RGB")

    # After processing we must still see head (red) near top and feet (green) near bottom.
    top_pixel = result.getpixel((result.width // 2, 5))
    bottom_pixel = result.getpixel((result.width // 2, result.height - 5))

    assert top_pixel[0] > 200 and top_pixel[1] < 50  # still red-ish
    assert bottom_pixel[1] > 200 and bottom_pixel[0] < 50  # still green-ish
    assert result.height >= result.width  # portrait

import json

from bot.services.openrouter import build_outfit_tryon_prompt, build_outfit_tryon_request_payload


def test_outfit_prompt_task_and_garment_count():
    payload = json.loads(build_outfit_tryon_prompt(3))
    assert payload["task"] == "virtual_try_on_outfit"
    assert payload["inputs"]["garment_count"] == 3


def test_outfit_payload_has_four_images_for_three_garments():
    payload = build_outfit_tryon_request_payload(
        "google/gemini-3.1-flash-image", b"p", [b"g1", b"g2", b"g3"]
    )
    content = payload["messages"][0]["content"]
    image_parts = [p for p in content if p["type"] == "image_url"]
    assert len(image_parts) == 4

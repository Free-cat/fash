import json

from bot.services.openrouter import (
    build_add_item_tryon_prompt,
    build_add_item_tryon_request_payload,
)


def test_add_item_prompt_locks_existing_look():
    payload = json.loads(build_add_item_tryon_prompt())
    assert payload["task"] == "virtual_try_on_add_item"
    assert "image_1" in payload["inputs"]
    assert "image_2" in payload["inputs"]
    assert "keep_exact" in payload["identity_lock"]
    assert "existing_outfit" in payload["preserve"] or "current_outfit" in str(payload)


def test_add_item_request_payload_has_result_and_garment():
    payload = build_add_item_tryon_request_payload(
        "google/gemini-3.1-flash-image", b"result", b"garment"
    )
    assert payload["model"] == "google/gemini-3.1-flash-image"
    content = payload["messages"][0]["content"]
    assert any(part.get("type") == "image_url" for part in content)
    images = [part for part in content if part.get("type") == "image_url"]
    assert len(images) == 2

import json

from bot.services.openrouter import (
    DEFAULT_TRYON_MODEL,
    build_tryon_prompt,
    build_tryon_request_payload,
)


def test_tryon_prompt_is_valid_json():
    prompt = build_tryon_prompt()
    data = json.loads(prompt)

    assert data["task"] == "virtual_try_on"
    assert data["framing"]["full_body"] is True
    assert "head_to_toe" in data["framing"]["requirements"]
    assert "no_cropped_legs" in data["framing"]["requirements"]
    assert "upper-body" not in prompt.lower()


def test_tryon_prompt_constant_matches_builder():
    from bot.services.openrouter import TRYON_PROMPT, build_tryon_prompt

    assert TRYON_PROMPT == build_tryon_prompt()
    assert "head_to_toe" in TRYON_PROMPT


def test_tryon_request_uses_recommended_model_and_portrait_config():
    payload = build_tryon_request_payload(
        DEFAULT_TRYON_MODEL,
        b"person",
        b"garment",
    )

    assert payload["model"] == "google/gemini-3.1-flash-image"
    assert payload["image_config"]["aspect_ratio"] == "3:4"
    assert payload["image_config"]["image_size"] == "1K"
    assert payload["modalities"] == ["image", "text"]

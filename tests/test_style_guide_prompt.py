import json

from bot.services.openrouter import (
    STYLE_GUIDE_ASPECT_RATIO,
    build_style_guide_prompt,
    build_style_guide_request_payload,
)


def test_style_guide_prompt_is_valid_json_with_required_keys():
    payload = json.loads(build_style_guide_prompt())
    assert payload["task"] == "personal_style_guide_board"
    assert payload["layout"]["format"] == "1:1 square"
    assert payload["content"]["outfits"] == "3-4 complete looks anchored on the featured garment"
    assert "identity_lock" in payload


def test_style_guide_request_uses_square_aspect_ratio():
    payload = build_style_guide_request_payload("google/gemini-3.1-flash-image", b"result")
    assert payload["image_config"]["aspect_ratio"] == STYLE_GUIDE_ASPECT_RATIO == "1:1"

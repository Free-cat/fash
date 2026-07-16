import json

from bot.services.openrouter import (
    DEFAULT_STYLE_GUIDE_MODEL,
    STYLE_GUIDE_ASPECT_RATIO,
    build_style_guide_prompt,
    build_style_guide_request_payload,
)


def test_style_guide_prompt_is_valid_json_with_required_keys():
    payload = json.loads(build_style_guide_prompt())
    assert payload["task"] == "personal_style_guide_board"
    assert payload["layout"]["format"] == "1:1 square"
    assert payload["layout"]["grid"]["top_left"]
    assert "8-10" in payload["layout"]["grid"]["right"]
    assert payload["content"]["outfits"]["category"] == "smart casual"
    assert payload["content"]["outfits"]["count"] == "8-10"
    assert "watch" in payload["content"]["accessories"]
    assert "identity_lock" in payload
    assert "style_analysis" in payload
    assert "Deep Autumn" in payload["style_analysis"]["display_on_board"][0]
    assert "illustration" in payload["negative"]
    assert payload["visual_style"]["rendering"]


def test_style_guide_request_uses_images_api_with_gpt_image_2():
    payload = build_style_guide_request_payload(
        DEFAULT_STYLE_GUIDE_MODEL, b"result"
    )
    assert payload["model"] == DEFAULT_STYLE_GUIDE_MODEL == "openai/gpt-image-2"
    assert payload["aspect_ratio"] == STYLE_GUIDE_ASPECT_RATIO == "1:1"
    assert payload["resolution"] == "1K"
    assert payload["quality"] == "high"
    assert len(payload["input_references"]) == 1
    ref = payload["input_references"][0]
    assert ref["type"] == "image_url"
    assert ref["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "prompt" in payload
    assert json.loads(payload["prompt"])["task"] == "personal_style_guide_board"
    assert "messages" not in payload

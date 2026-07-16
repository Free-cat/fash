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
    assert data["framing"]["policy"] == "source_adaptive"
    assert "conditional_outpaint" in data["framing"]
    assert "upper-body" not in prompt.lower()


def test_tryon_prompt_constant_matches_builder():
    from bot.services.openrouter import TRYON_PROMPT, build_tryon_prompt

    assert TRYON_PROMPT == build_tryon_prompt()
    assert "source_adaptive" in TRYON_PROMPT


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


def test_tryon_request_labels_target_person_and_outfit_source_images():
    payload = build_tryon_request_payload(
        DEFAULT_TRYON_MODEL,
        b"person",
        b"garment",
    )
    content = payload["messages"][0]["content"]

    assert content[1] == {
        "type": "text",
        "text": (
            "TARGET PERSON (IMAGE 1): Dress this exact person. Preserve this "
            "person's identity, face, body, pose, proportions, and background."
        ),
    }
    assert content[2]["type"] == "image_url"
    assert content[3] == {
        "type": "text",
        "text": (
            "OUTFIT SOURCE (IMAGE 2): Transfer clothing, shoes, accessories, "
            "and styling only. Never transfer this person's identity or body."
        ),
    }
    assert content[4]["type"] == "image_url"


def test_tryon_prompt_uses_conditional_outpainting_without_changing_proportions():
    data = json.loads(build_tryon_prompt())

    assert data["framing"]["policy"] == "source_adaptive"
    assert data["framing"]["preserve_first"] == [
        "body_scale",
        "body_proportions",
        "pose",
        "subject_position",
        "camera_perspective",
    ]
    assert data["framing"]["outpaint_only_if"] == (
        "the source image genuinely cuts off lower legs or feet at the frame edge"
    )
    assert data["framing"]["never"] == [
        "shorten_or_compress_legs",
        "shrink_the_person_to_force_full_body",
        "invent_childlike_proportions",
        "change_pose_to_fit_the_canvas",
    ]
    assert "mandatory" not in data["output"]


def test_tryon_prompt_transfers_full_outfit_from_source_model_not_identity():
    data = json.loads(build_tryon_prompt())

    assert data["source_model_rule"]["default_behavior"] == (
        "if image_2 contains a person wearing clothing, treat that person only as an outfit donor"
    )
    assert data["source_model_rule"]["extract"] == [
        "all_visible_garments",
        "shoes",
        "accessories",
        "layering",
        "styling_cues",
    ]
    assert data["source_model_rule"]["ignore_donor"] == [
        "face",
        "body",
        "skin",
        "hair",
        "age",
        "gender_presentation",
        "pose",
        "background",
    ]
    assert data["source_model_rule"]["transfer_to"] == "image_1 person only"

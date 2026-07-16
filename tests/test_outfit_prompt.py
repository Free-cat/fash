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


def test_outfit_request_labels_target_before_person_and_each_source_before_image():
    payload = build_outfit_tryon_request_payload(
        "google/gemini-3.1-flash-image", b"p", [b"g1", b"g2"]
    )
    content = payload["messages"][0]["content"]

    assert content[1]["text"].startswith("TARGET PERSON (IMAGE 1):")
    assert content[2]["type"] == "image_url"
    assert content[3]["text"].startswith("OUTFIT SOURCE (IMAGE 2):")
    assert content[4]["type"] == "image_url"
    assert content[5]["text"].startswith("OUTFIT SOURCE (IMAGE 3):")
    assert content[6]["type"] == "image_url"


def test_outfit_prompt_uses_source_adaptive_framing():
    payload = json.loads(build_outfit_tryon_prompt(3))

    assert payload["framing"]["policy"] == "source_adaptive"
    assert payload["framing"]["outpaint_only_if"].startswith(
        "the source image genuinely cuts off"
    )
    assert "shorten_or_compress_legs" in payload["framing"]["never"]
    assert "mandatory" not in payload["output"]


def test_outfit_prompt_combines_source_model_outfits_with_garment_only_photos():
    payload = json.loads(build_outfit_tryon_prompt(3))

    assert payload["source_model_rule"]["default_behavior"] == (
        "any garment image may be either a standalone product photo or a person wearing an outfit"
    )
    assert payload["source_model_rule"]["if_image_contains_person"] == (
        "extract the full visible outfit from that donor person"
    )
    assert payload["source_model_rule"]["combine"] == (
        "combine standalone garments and donor outfits into one cohesive look on image_1 person"
    )
    assert "donor_face" in payload["source_model_rule"]["never_transfer"]

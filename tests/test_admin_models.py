import pytest

from bot.services.model_catalog import (
    PAGE_SIZE,
    ModelCatalog,
    _filter_style_guide_models,
    _filter_tryon_models,
    model_short_label,
)


def test_filter_tryon_models_requires_image_input_and_output():
    body = {
        "data": [
            {
                "id": "google/gemini-3.1-flash-image",
                "architecture": {
                    "input_modalities": ["image", "text"],
                    "output_modalities": ["image", "text"],
                },
            },
            {
                "id": "openai/gpt-4o",
                "architecture": {
                    "input_modalities": ["text"],
                    "output_modalities": ["text"],
                },
            },
        ]
    }
    assert _filter_tryon_models(body) == ["google/gemini-3.1-flash-image"]


def test_filter_style_guide_models_requires_input_references():
    body = [
        {
            "id": "openai/gpt-image-2",
            "supported_parameters": {
                "input_references": {"type": "range", "min": 0, "max": 14},
            },
        },
        {
            "id": "bytedance-seed/seedream-4.5",
            "supported_parameters": {},
        },
    ]
    assert _filter_style_guide_models(body) == ["openai/gpt-image-2"]


def test_model_catalog_page():
    catalog = ModelCatalog("test-key")
    catalog._tryon_models = [f"m{i}" for i in range(20)]
    page_models, total_pages = catalog.page("tryon", 1)
    assert len(page_models) == PAGE_SIZE
    assert total_pages == 3
    assert page_models[0] == "m8"


def test_model_short_label_marks_active():
    assert model_short_label("google/gemini-3.1-flash-image", active=True).startswith("✓")


@pytest.mark.asyncio
async def test_bot_settings_roundtrip(tmp_path):
    from bot.db.database import Database

    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.set_bot_setting("tryon_model", "google/gemini-3.1-flash-image")
    await db.set_bot_setting("style_guide_model", "openai/gpt-image-2")
    assert await db.get_bot_setting("tryon_model") == "google/gemini-3.1-flash-image"
    assert await db.get_bot_setting("style_guide_model") == "openai/gpt-image-2"
    await db.close()

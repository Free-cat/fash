from __future__ import annotations

import time

import aiohttp

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_IMAGE_MODELS_URL = "https://openrouter.ai/api/v1/images/models"

CACHE_TTL_SECONDS = 300
PAGE_SIZE = 8


class ModelCatalog:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._tryon_models: list[str] = []
        self._style_guide_models: list[str] = []
        self._fetched_at: float = 0.0

    @property
    def tryon_models(self) -> list[str]:
        return list(self._tryon_models)

    @property
    def style_guide_models(self) -> list[str]:
        return list(self._style_guide_models)

    async def ensure_fresh(self, *, force: bool = False) -> None:
        if (
            not force
            and self._tryon_models
            and self._style_guide_models
            and time.monotonic() - self._fetched_at < CACHE_TTL_SECONDS
        ):
            return
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                OPENROUTER_MODELS_URL, headers=headers, timeout=30
            ) as response:
                body = await response.json()
                if response.status >= 400:
                    raise RuntimeError(f"OpenRouter models error: {body}")

            async with session.get(
                OPENROUTER_IMAGE_MODELS_URL, headers=headers, timeout=30
            ) as response:
                image_body = await response.json()
                if response.status >= 400:
                    raise RuntimeError(f"OpenRouter image models error: {image_body}")

        self._tryon_models = _filter_tryon_models(body)
        self._style_guide_models = _filter_style_guide_models(image_body)
        self._fetched_at = time.monotonic()

    def page(self, kind: str, page: int) -> tuple[list[str], int]:
        models = self._tryon_models if kind == "tryon" else self._style_guide_models
        total_pages = max(1, (len(models) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, total_pages - 1))
        start = page * PAGE_SIZE
        return models[start : start + PAGE_SIZE], total_pages


def _filter_tryon_models(body: dict | list) -> list[str]:
    items = body if isinstance(body, list) else body.get("data", [])
    models: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        arch = item.get("architecture") or {}
        inputs = arch.get("input_modalities") or []
        outputs = arch.get("output_modalities") or []
        model_id = item.get("id")
        if model_id and "image" in inputs and "image" in outputs:
            models.append(model_id)
    return sorted(set(models))


def _filter_style_guide_models(body: dict | list) -> list[str]:
    items = body if isinstance(body, list) else body.get("data", [])
    models: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        refs = (item.get("supported_parameters") or {}).get("input_references") or {}
        max_refs = refs.get("max", 0) if isinstance(refs, dict) else 0
        model_id = item.get("id")
        if model_id and max_refs > 0:
            models.append(model_id)
    return sorted(set(models))


def model_short_label(model_id: str, *, active: bool = False) -> str:
    short = model_id.split("/")[-1]
    if len(short) > 26:
        short = short[:23] + "..."
    prefix = "✓ " if active else ""
    return f"{prefix}{short}"

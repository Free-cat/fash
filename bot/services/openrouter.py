from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path

import aiohttp

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# GA image-editing models on OpenRouter (Jul 2026):
# - google/gemini-3.1-flash-image  — best balance for try-on (recommended)
# - google/gemini-2.5-flash-image  — cheaper fallback
# - google/gemini-3-pro-image      — highest quality, ~4× cost
DEFAULT_TRYON_MODEL = "google/gemini-3.1-flash-image"
TRYON_ASPECT_RATIO = "3:4"
TRYON_IMAGE_SIZE = "1K"
STYLE_GUIDE_ASPECT_RATIO = "1:1"
STYLE_GUIDE_IMAGE_SIZE = "1K"


def build_tryon_prompt() -> str:
    """Structured JSON prompt for Gemini image try-on via OpenRouter."""
    payload = {
        "task": "virtual_try_on",
        "role": "expert virtual stylist and photorealistic image compositor",
        "inputs": {
            "image_1": "person reference photo",
            "image_2": "garment / clothing item photo",
        },
        "goal": (
            "Dress the person from image_1 in the garment from image_2. "
            "Output one photorealistic photo of that same person wearing the garment."
        ),
        "identity_lock": {
            "keep_exact": [
                "face",
                "facial_features",
                "hair",
                "skin_tone",
                "body_shape",
                "body_proportions",
                "pose",
                "stance",
                "camera_angle",
                "background",
                "lighting_direction",
            ],
            "do_not": [
                "change_identity",
                "beautify_face",
                "alter_age",
                "change_gender_presentation",
                "replace_background",
            ],
        },
        "garment_rules": {
            "apply": "the clothing item from image_2 onto the person from image_1",
            "match": [
                "color",
                "pattern",
                "texture",
                "silhouette",
                "length",
                "neckline",
                "sleeves",
                "fabric_drape",
            ],
            "fit": "natural body-conforming fit with realistic wrinkles and shadows",
            "if_garment_on_model": (
                "extract only the clothing; ignore the other person's body and face"
            ),
        },
        "framing": {
            "full_body": True,
            "aspect_ratio": "3:4 portrait",
            "requirements": [
                "head_to_toe",
                "entire_person_visible",
                "include_feet_and_shoes",
                "include_head_and_hair",
                "no_cropped_legs",
                "no_cropped_head",
                "no_waist_up_crop",
                "no_close_up",
            ],
            "camera": "same distance and framing as image_1, or slightly wider if needed to keep full body",
        },
        "quality": {
            "style": "photorealistic fashion photo",
            "lighting": "natural, consistent with image_1",
            "details": [
                "sharp fabric texture",
                "realistic shadows under garment",
                "correct perspective",
                "no plastic skin",
                "no warped limbs",
                "no extra fingers",
                "no text overlays",
                "no watermarks",
            ],
        },
        "output": {
            "count": 1,
            "type": "single_image",
            "format": "photorealistic_try_on_result",
            "mandatory": "full body of the person must be fully visible from head to toes",
        },
        "negative": [
            "cropped legs",
            "cut off feet",
            "upper body only",
            "waist up",
            "portrait crop",
            "close-up face",
            "second person",
            "mannequin",
            "flat lay only",
            "cartoon",
            "anime",
            "low resolution",
            "blurry",
            "distorted anatomy",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


TRYON_PROMPT = build_tryon_prompt()


def build_outfit_tryon_prompt(garment_count: int) -> str:
    """Structured JSON prompt for multi-garment outfit try-on via OpenRouter."""
    garment_inputs = {
        f"image_{i + 2}": f"garment / clothing item photo {i + 1} of {garment_count}"
        for i in range(garment_count)
    }
    garment_refs = ", ".join(f"image_{i + 2}" for i in range(garment_count))
    payload = {
        "task": "virtual_try_on_outfit",
        "role": "expert virtual stylist and photorealistic image compositor",
        "inputs": {
            "image_1": "person reference photo",
            **garment_inputs,
            "garment_count": garment_count,
        },
        "goal": (
            f"Dress the person from image_1 in ALL {garment_count} garments "
            f"({garment_refs}) as one cohesive outfit. "
            "Output one photorealistic photo of that same person wearing the complete look."
        ),
        "identity_lock": {
            "keep_exact": [
                "face",
                "facial_features",
                "hair",
                "skin_tone",
                "body_shape",
                "body_proportions",
                "pose",
                "stance",
                "camera_angle",
                "background",
                "lighting_direction",
            ],
            "do_not": [
                "change_identity",
                "beautify_face",
                "alter_age",
                "change_gender_presentation",
                "replace_background",
            ],
        },
        "garment_rules": {
            "apply": (
                f"all {garment_count} clothing items onto the person from image_1 "
                "as a single cohesive outfit"
            ),
            "infer_roles": [
                "top",
                "bottom",
                "outerwear",
                "dress",
                "shoes",
                "accessories",
            ],
            "no_duplicate_layers": (
                "do not add extra layers beyond the provided garments "
                "unless a garment clearly requires it"
            ),
            "match": [
                "color",
                "pattern",
                "texture",
                "silhouette",
                "length",
                "neckline",
                "sleeves",
                "fabric_drape",
            ],
            "fit": "natural body-conforming fit with realistic wrinkles and shadows",
            "if_garment_on_model": (
                "extract only the clothing; ignore the other person's body and face"
            ),
        },
        "framing": {
            "full_body": True,
            "aspect_ratio": "3:4 portrait",
            "requirements": [
                "head_to_toe",
                "entire_person_visible",
                "include_feet_and_shoes",
                "include_head_and_hair",
                "no_cropped_legs",
                "no_cropped_head",
                "no_waist_up_crop",
                "no_close_up",
            ],
            "camera": "same distance and framing as image_1, or slightly wider if needed to keep full body",
        },
        "quality": {
            "style": "photorealistic fashion photo",
            "lighting": "natural, consistent with image_1",
            "details": [
                "sharp fabric texture",
                "realistic shadows under garment",
                "correct perspective",
                "no plastic skin",
                "no warped limbs",
                "no extra fingers",
                "no text overlays",
                "no watermarks",
            ],
        },
        "output": {
            "count": 1,
            "type": "single_image",
            "format": "photorealistic_outfit_try_on_result",
            "mandatory": "full body of the person must be fully visible from head to toes",
        },
        "negative": [
            "cropped legs",
            "cut off feet",
            "upper body only",
            "waist up",
            "portrait crop",
            "close-up face",
            "second person",
            "mannequin",
            "flat lay only",
            "cartoon",
            "anime",
            "low resolution",
            "blurry",
            "distorted anatomy",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_style_guide_prompt() -> str:
    """Structured JSON prompt for personal style guide board via OpenRouter."""
    payload = {
        "task": "personal_style_guide_board",
        "role": "expert fashion stylist and editorial layout designer",
        "inputs": {
            "image_1": "try-on result image (person wearing the featured garment)",
        },
        "goal": (
            "Create one editorial style guide board anchored on the featured garment "
            "from image_1. Infer style season/type, skin undertone, and complementary "
            "colors from the image — do not assume gender or hardcode season names."
        ),
        "identity_lock": {
            "keep_exact": [
                "face",
                "facial_features",
                "skin_tone",
                "hair",
            ],
            "do_not": [
                "change_identity",
                "beautify_face",
                "alter_age",
                "change_gender_presentation",
                "distort_face",
                "distort_skin_texture",
            ],
        },
        "layout": {
            "format": "1:1 square",
            "grid": {
                "top_left": "portrait of the same person from image_1",
                "right": "3-4 outfit combinations",
                "bottom": "color palette (5-7 swatches) and 2-3 accessories",
            },
        },
        "content": {
            "outfits": "3-4 complete looks anchored on the featured garment",
            "palette": "5-7 complementary color swatches inferred from image_1",
            "accessories": "2-3 accessory suggestions that pair with the featured garment",
        },
        "style": {
            "aesthetic": "minimal, modern, magazine editorial",
            "background": "soft warm beige #F5F0EB",
            "grid": "clean layout with readable labels",
        },
        "inference": {
            "from_image": [
                "style_season_or_type",
                "skin_undertone_warm_cool_or_neutral",
                "complementary_colors",
            ],
            "do_not_hardcode": [
                "gender",
                "season_names",
            ],
        },
        "quality": {
            "details": [
                "natural skin texture",
                "no distortion",
                "sharp readable labels",
                "no watermarks",
                "no text overlays beyond board labels",
            ],
        },
        "output": {
            "count": 1,
            "type": "single_image",
            "format": "personal_style_guide_board",
        },
        "negative": [
            "different person",
            "cluttered layout",
            "watermarks",
            "cartoon",
            "anime",
            "cropped face",
            "low resolution",
            "blurry",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


STYLE_GUIDE_PROMPT = build_style_guide_prompt()


def build_tryon_request_payload(
    model: str,
    person_image: bytes,
    garment_image: bytes,
) -> dict:
    return {
        "model": model,
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": TRYON_ASPECT_RATIO,
            "image_size": TRYON_IMAGE_SIZE,
        },
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_tryon_prompt()},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _as_data_uri(person_image, "image/jpeg"),
                        },
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _as_data_uri(garment_image, "image/jpeg"),
                        },
                    },
                ],
            }
        ],
    }


def build_outfit_tryon_request_payload(
    model: str,
    person: bytes,
    garments: list[bytes],
) -> dict:
    content: list[dict] = [
        {"type": "text", "text": build_outfit_tryon_prompt(len(garments))},
        {
            "type": "image_url",
            "image_url": {
                "url": _as_data_uri(person, "image/jpeg"),
            },
        },
    ]
    for garment in garments:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": _as_data_uri(garment, "image/jpeg"),
                },
            }
        )
    return {
        "model": model,
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": TRYON_ASPECT_RATIO,
            "image_size": TRYON_IMAGE_SIZE,
        },
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
    }


def build_style_guide_request_payload(
    model: str,
    result_image: bytes,
) -> dict:
    return {
        "model": model,
        "modalities": ["image", "text"],
        "image_config": {
            "aspect_ratio": STYLE_GUIDE_ASPECT_RATIO,
            "image_size": STYLE_GUIDE_IMAGE_SIZE,
        },
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_style_guide_prompt()},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _as_data_uri(result_image, "image/jpeg"),
                        },
                    },
                ],
            }
        ],
    }


class TryOnError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    async def generate_tryon(
        self, person_image: bytes, garment_image: bytes
    ) -> bytes:
        payload = build_tryon_request_payload(
            self.model, person_image, garment_image
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/primerka_bot",
            "X-Title": "FitRoom Try-On Bot",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_URL, json=payload, headers=headers, timeout=120
            ) as response:
                body = await response.json()
                if response.status >= 400:
                    message = body.get("error", {}).get("message", str(body))
                    raise TryOnError(f"OpenRouter error: {message}")

        image_bytes = _extract_image_bytes(body)
        if not image_bytes:
            raise TryOnError("Model returned no image. Try different photos.")
        return image_bytes

    async def generate_outfit_tryon(
        self, person: bytes, garments: list[bytes]
    ) -> bytes:
        if len(garments) == 1:
            return await self.generate_tryon(person, garments[0])

        payload = build_outfit_tryon_request_payload(
            self.model, person, garments
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/primerka_bot",
            "X-Title": "FitRoom Try-On Bot",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_URL, json=payload, headers=headers, timeout=120
            ) as response:
                body = await response.json()
                if response.status >= 400:
                    message = body.get("error", {}).get("message", str(body))
                    raise TryOnError(f"OpenRouter error: {message}")

        image_bytes = _extract_image_bytes(body)
        if not image_bytes:
            raise TryOnError("Model returned no image. Try different photos.")
        return image_bytes

    async def generate_style_guide(self, result_image: bytes) -> bytes:
        payload = build_style_guide_request_payload(self.model, result_image)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/primerka_bot",
            "X-Title": "FitRoom Try-On Bot",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_URL, json=payload, headers=headers, timeout=120
            ) as response:
                body = await response.json()
                if response.status >= 400:
                    message = body.get("error", {}).get("message", str(body))
                    raise TryOnError(f"OpenRouter error: {message}")

        image_bytes = _extract_image_bytes(body)
        if not image_bytes:
            raise TryOnError("Model returned no image. Try different photos.")
        return image_bytes


def _as_data_uri(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _extract_image_bytes(response: dict) -> bytes | None:
    choices = response.get("choices") or []
    if not choices:
        return None

    message = choices[0].get("message") or {}
    parts = message.get("images") or message.get("content")

    if isinstance(parts, list):
        for part in parts:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "image_url":
                url = part.get("image_url", {}).get("url", "")
                decoded = _decode_data_uri(url)
                if decoded:
                    return decoded
            if part.get("type") == "image":
                data = part.get("image", {}).get("data") or part.get("data")
                if data:
                    return base64.b64decode(data)

    if isinstance(parts, str):
        decoded = _decode_data_uri(parts)
        if decoded:
            return decoded

    return None


def _decode_data_uri(value: str) -> bytes | None:
    match = re.match(r"data:image/[^;]+;base64,(.+)", value)
    if not match:
        return None
    return base64.b64decode(match.group(1))


class FileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def user_dir(self, telegram_id: int) -> Path:
        path = self.root / str(telegram_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_person_photo(self, telegram_id: int, index: int, data: bytes) -> Path:
        path = self.user_dir(telegram_id) / f"person_{index}.jpg"
        path.write_bytes(data)
        return path

    def save_garment_photo(self, telegram_id: int, generation_id: int, data: bytes) -> Path:
        path = self.user_dir(telegram_id) / f"garment_{generation_id}.jpg"
        path.write_bytes(data)
        return path

    def save_result_photo(self, telegram_id: int, generation_id: int, data: bytes) -> Path:
        path = self.user_dir(telegram_id) / f"result_{generation_id}.jpg"
        path.write_bytes(data)
        return path

    def save_style_guide_photo(
        self, telegram_id: int, generation_id: int, data: bytes
    ) -> Path:
        path = self.user_dir(telegram_id) / f"style_guide_{generation_id}.jpg"
        path.write_bytes(data)
        return path

    def read(self, path: str | Path) -> bytes:
        return Path(path).read_bytes()

    def delete_user_dir(self, telegram_id: int) -> None:
        path = self.root / str(telegram_id)
        if path.exists():
            shutil.rmtree(path)

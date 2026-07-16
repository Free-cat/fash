from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path

import aiohttp

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"

# GA image-editing models on OpenRouter (Jul 2026):
# - google/gemini-3.1-flash-image  — best balance for try-on (recommended)
# - google/gemini-2.5-flash-image  — cheaper fallback
# - google/gemini-3-pro-image      — highest quality, ~4× cost
DEFAULT_TRYON_MODEL = "google/gemini-3.1-flash-image"
# Style guide boards: gemini-3-pro-image for highest quality editorial layout
DEFAULT_STYLE_GUIDE_MODEL = "google/gemini-3-pro-image"
TRYON_ASPECT_RATIO = "3:4"
TRYON_IMAGE_SIZE = "1K"
STYLE_GUIDE_ASPECT_RATIO = "1:1"
STYLE_GUIDE_IMAGE_SIZE = "1K"
TARGET_PERSON_LABEL = (
    "TARGET PERSON (IMAGE 1): Dress this exact person. Preserve this person's "
    "identity, face, body, pose, proportions, and background."
)


def _outfit_source_label(image_number: int) -> str:
    return (
        f"OUTFIT SOURCE (IMAGE {image_number}): Transfer clothing, shoes, "
        "accessories, and styling only. Never transfer this person's identity or body."
    )


def _source_adaptive_framing() -> dict:
    """Preserve source geometry; outpaint only genuinely missing lower body."""
    return {
        "policy": "source_adaptive",
        "aspect_ratio": "3:4 portrait",
        "inspect_before_editing": (
            "First determine whether the person's lower legs and feet are already "
            "visible in image_1 or are genuinely cut off by the frame edge."
        ),
        "preserve_first": [
            "body_scale",
            "body_proportions",
            "pose",
            "subject_position",
            "camera_perspective",
        ],
        "if_person_is_fully_visible": (
            "Preserve the original framing exactly. Do not zoom, shrink, reposition, "
            "or extend the person."
        ),
        "outpaint_only_if": (
            "the source image genuinely cuts off lower legs or feet at the frame edge"
        ),
        "conditional_outpaint": (
            "Extend the canvas downward only as much as needed. Continue the existing "
            "legs at their anatomically correct length and perspective, add natural "
            "feet or shoes consistent with the outfit, and preserve the original "
            "upper body size, pose, and location. Use available background context; "
            "do not compress the person to make room."
        ),
        "never": [
            "shorten_or_compress_legs",
            "shrink_the_person_to_force_full_body",
            "invent_childlike_proportions",
            "change_pose_to_fit_the_canvas",
        ],
    }


def _single_source_model_rule() -> dict:
    return {
        "default_behavior": (
            "if image_2 contains a person wearing clothing, treat that person only as an outfit donor"
        ),
        "extract": [
            "all_visible_garments",
            "shoes",
            "accessories",
            "layering",
            "styling_cues",
        ],
        "ignore_donor": [
            "face",
            "body",
            "skin",
            "hair",
            "age",
            "gender_presentation",
            "pose",
            "background",
        ],
        "transfer_to": "image_1 person only",
        "identity_priority": (
            "The final person must always be the person from image_1. Never copy "
            "the donor person's identity, body, pose, proportions, or background."
        ),
    }


def _multi_source_model_rule() -> dict:
    return {
        "default_behavior": (
            "any garment image may be either a standalone product photo or a person wearing an outfit"
        ),
        "if_image_contains_person": "extract the full visible outfit from that donor person",
        "extract": [
            "all_visible_garments",
            "shoes",
            "accessories",
            "layering",
            "styling_cues",
        ],
        "combine": (
            "combine standalone garments and donor outfits into one cohesive look on image_1 person"
        ),
        "conflict_resolution": (
            "if multiple donor or product images provide the same category, prefer "
            "the most visually prominent or most recently provided garment"
        ),
        "never_transfer": [
            "donor_face",
            "donor_body",
            "donor_skin",
            "donor_hair",
            "donor_age",
            "donor_gender_presentation",
            "donor_pose",
            "donor_background",
        ],
        "transfer_to": "image_1 person only",
    }


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
                "extract the full visible outfit, including shoes and accessories; "
                "ignore the other person's body, face, pose, and background"
            ),
        },
        "source_model_rule": _single_source_model_rule(),
        "edit_scope": (
            "Change only the clothing and its natural occlusion, wrinkles, and shadows. "
            "Keep all visible person and background pixels as close to image_1 as possible, "
            "except for conditional lower-frame outpainting described below."
        ),
        "framing": _source_adaptive_framing(),
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
            "priority": (
                "identity and natural adult body proportions take precedence over "
                "showing feet when both cannot be achieved reliably"
            ),
        },
        "negative": [
            "shortened legs",
            "compressed body",
            "childlike body proportions",
            "unnecessary zoom out",
            "unnecessary outpainting",
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
                "extract the full visible outfit, including shoes and accessories; "
                "ignore the other person's body, face, pose, and background"
            ),
        },
        "source_model_rule": _multi_source_model_rule(),
        "edit_scope": (
            "Change only the clothing and its natural occlusion, wrinkles, and shadows. "
            "Keep all visible person and background pixels as close to image_1 as possible, "
            "except for conditional lower-frame outpainting described below."
        ),
        "framing": _source_adaptive_framing(),
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
            "priority": (
                "identity and natural adult body proportions take precedence over "
                "showing feet when both cannot be achieved reliably"
            ),
        },
        "negative": [
            "shortened legs",
            "compressed body",
            "childlike body proportions",
            "unnecessary zoom out",
            "unnecessary outpainting",
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
    """Structured JSON prompt for photorealistic personal style guide board."""
    payload = {
        "task": "personal_style_guide_board",
        "role": "professional personal stylist and editorial layout designer",
        "input": {
            "reference_image": (
                "try-on result photo — person wearing the featured garment"
            ),
        },
        "goal": (
            "Create one clean, modern, photorealistic personal style guide board "
            "anchored on the featured garment from the reference image. Infer "
            "style type, undertone, and best colors from the person and outfit — "
            "do not assume gender or hardcode season/color names."
        ),
        "identity_lock": {
            "keep_exact": [
                "face",
                "facial_features",
                "skin_tone",
                "hair",
                "body_type",
                "proportions",
            ],
            "apply_to": "portrait and every outfit panel",
            "do_not": [
                "change_identity",
                "beautify_face",
                "alter_age",
                "distort_face",
                "distort_skin_texture",
            ],
        },
        "featured_garment": {
            "source": "reference_image",
            "preserve": [
                "cut",
                "color",
                "fabric",
                "texture",
                "buttons",
                "pockets",
                "silhouette",
            ],
            "rule": "every outfit combination must anchor on this exact piece",
        },
        "layout": {
            "format": "1:1 square",
            "grid": {
                "top_left": (
                    "realistic portrait of the same person wearing the featured "
                    "garment from the reference"
                ),
                "right": (
                    "8-10 smart casual outfit combinations on the same person, "
                    "each in a clean labeled panel with short English style names"
                ),
                "bottom": (
                    "color palette swatches plus accessory suggestions "
                    "(watch, belt, shoes, sunglasses, bag)"
                ),
            },
            "background": "soft warm beige #F5F0EB",
            "structure": "minimal, modern, magazine-style clean grid",
        },
        "style_analysis": {
            "infer_from_reference": [
                "style_type_season",
                "undertone_warm_cool_or_neutral",
                "best_complementary_colors",
            ],
            "display_on_board": [
                "style_type label (e.g. Deep Autumn)",
                "undertone label (e.g. Warm/Neutral)",
                "best colors list (e.g. greens, browns, navy, beige)",
            ],
            "do_not_hardcode": ["gender", "season_names", "color_names"],
        },
        "content": {
            "outfits": {
                "count": "8-10",
                "category": "smart casual",
                "requirements": [
                    "complete wearable looks",
                    "layers, bottoms, shoes",
                    "balanced proportions",
                    "complementary to inferred undertone",
                ],
            },
            "palette": "5-7 named color swatches from inferred best colors",
            "accessories": [
                "watch",
                "belt",
                "shoes",
                "sunglasses",
                "bag",
            ],
        },
        "visual_style": {
            "aesthetic": "minimal, modern, magazine editorial",
            "rendering": (
                "hyper-realistic fashion photography / editorial lookbook"
            ),
            "details": [
                "realistic skin texture",
                "natural fabric drape and weave",
                "soft studio or natural daylight",
                "sharp readable labels",
            ],
        },
        "quality": {
            "must_have": [
                "same face in all outfit panels",
                "natural skin texture",
                "no distortion",
                "no watermarks",
            ],
        },
        "negative": [
            "different person",
            "illustration",
            "drawing",
            "flat vector art",
            "cartoon",
            "anime",
            "CGI",
            "painted",
            "line art",
            "cluttered layout",
            "watermarks",
            "blurry",
            "low resolution",
        ],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


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
                    {"type": "text", "text": TARGET_PERSON_LABEL},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": _as_data_uri(person_image, "image/jpeg"),
                        },
                    },
                    {"type": "text", "text": _outfit_source_label(2)},
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
        {"type": "text", "text": TARGET_PERSON_LABEL},
        {
            "type": "image_url",
            "image_url": {
                "url": _as_data_uri(person, "image/jpeg"),
            },
        },
    ]
    for index, garment in enumerate(garments, start=2):
        content.extend(
            [
                {"type": "text", "text": _outfit_source_label(index)},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": _as_data_uri(garment, "image/jpeg"),
                    },
                },
            ]
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
        "prompt": build_style_guide_prompt(),
        "aspect_ratio": STYLE_GUIDE_ASPECT_RATIO,
        "resolution": STYLE_GUIDE_IMAGE_SIZE,
        "quality": "high",
        "input_references": [
            {
                "type": "image_url",
                "image_url": {
                    "url": _as_data_uri(result_image, "image/jpeg"),
                },
            }
        ],
    }


class TryOnError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        style_guide_model: str = DEFAULT_STYLE_GUIDE_MODEL,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.style_guide_model = style_guide_model

    def set_tryon_model(self, model: str) -> None:
        self.model = model

    def set_style_guide_model(self, model: str) -> None:
        self.style_guide_model = model

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
        payload = build_style_guide_request_payload(
            self.style_guide_model, result_image
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/primerka_bot",
            "X-Title": "FitRoom Try-On Bot",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_IMAGES_URL, json=payload, headers=headers, timeout=240
            ) as response:
                body = await response.json()
                if response.status >= 400:
                    message = body.get("error", {}).get("message", str(body))
                    raise TryOnError(f"OpenRouter error: {message}")

        image_bytes = _extract_images_api_bytes(body)
        if not image_bytes:
            raise TryOnError("Model returned no image. Try different photos.")
        return image_bytes


def _as_data_uri(data: bytes, mime: str) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _extract_images_api_bytes(response: dict) -> bytes | None:
    for item in response.get("data") or []:
        if not isinstance(item, dict):
            continue
        encoded = item.get("b64_json")
        if encoded:
            return base64.b64decode(encoded)
        url = (item.get("url") or "").strip()
        if url.startswith("data:"):
            decoded = _decode_data_uri(url)
            if decoded:
                return decoded
    return None


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

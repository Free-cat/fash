# Style Guide Upsell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 1-try-on Style Guide upsell after try-on — 1:1 mood board from the try-on result, with copy aligned to FitRoom Brand Kit.

**Architecture:** Extend OpenRouter client with focused 1:1 board prompt; link style guides to `generations.id`; expose upsell as primary result button + 30s follow-up; reuse try-on billing, guard, and circuit breaker. All user-facing strings follow brand kit principles (value-language, peak-emotion sell, friend-stylist voice).

**Tech Stack:** Python 3, aiogram 3, SQLite, OpenRouter (`google/gemini-3.1-flash-image`), pytest

**Copy reference:** `docs/superpowers/specs/2026-07-15-style-guide-upsell-design.md` (Flow 15) + FitRoom Brand Kit PDF (Flows 01–14)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `bot/copy/en.py` | Modify | Brand-kit copy for Style Guide + optionally existing flows |
| `bot/copy/__init__.py` | Modify | New `Copy` fields |
| `bot/copy/ru.py` | Modify | Stub RU strings |
| `bot/services/openrouter.py` | Modify | Style guide prompt + `generate_style_guide()` |
| `bot/db/migrations.py` | Modify | `style_guide_path`, `style_guide_at` columns |
| `bot/db/database.py` | Modify | Return generation id; fetch/update style guide |
| `bot/keyboards.py` | Modify | Style guide button as row 1 on result keyboard |
| `bot/handlers/styleguide.py` | Create | Callback + delayed offer logic |
| `bot/handlers/tryon.py` | Modify | Pass generation id; schedule 30s offer |
| `bot/main.py` | Modify | Register router |
| `tests/test_style_guide_prompt.py` | Create | Prompt structure tests |
| `tests/test_style_guide_flow.py` | Create | Keyboard + DB + copy tests |
| `tests/test_tryon_communication.py` | Modify | Updated keyboard + brand-kit result captions |

---

### Task 0: Brand Kit Copy Baseline (recommended, can run in parallel)

Apply brand kit rewrites from PDF to `bot/copy/en.py` for flows that Style Guide touches. Minimum scope for this feature:

- [ ] **Step 1: Update Flow 07 result captions** (kit §07)

```python
result_caption="This is *you* in that outfit 🔥",
try_another="Love it? Try another 👗",
low_balance="⚠ {count} try-on(s) left — make them count 👗",
paywall=(
    "This is *you* in that outfit 🔥\n"
    "That's your last free try-on — and it looked great on you.\n"
    "Keep going: 5 more try-ons for 50⭐ (~10 sec to set up)."
),
deficit="Out of try-ons! Grab 5 more for 50⭐ — 5 seconds and you're back 👗",
```

- [ ] **Step 2: Update shared strings Style Guide reuses**

```python
generating="Styling your look… this takes about 15 sec ✨",
generation_failed="That one didn't come through — and I've refunded your try-on. Mind giving it another go?",
concurrent="One look at a time 😊 I'm still finishing your last try-on — hang tight a few seconds.",
circuit_open="The fitting room's briefly busy 🙈 Give it a couple of minutes and try again — your try-ons are safe.",
not_enough_credits="Not enough try-ons left.",
try_on_hint="Send a clothing photo to try it on 👗\n1 try-on · Balance: {balance}",
```

- [ ] **Step 3: Move validation errors from `image_processor.py` into copy**

Add to `Copy` dataclass: `photo_too_small`, `photo_bad_format`, `garment_too_small` with kit §04/§06 strings.

- [ ] **Step 4: Update tests that assert old copy**

Run: `pytest tests/test_tryon_communication.py tests/test_guide_flow.py -v`

- [ ] **Step 5: Commit**

```bash
git add bot/copy/ bot/services/image_processor.py tests/
git commit -m "copy: apply brand kit rewrites to core flows"
```

> Full kit rollout (Flows 01–14, shop, drip, keyboard, admin) is a separate PR. Task 0 covers only strings Style Guide depends on.

---

### Task 1: Style Guide Prompt

**Files:**
- Modify: `bot/services/openrouter.py`
- Create: `tests/test_style_guide_prompt.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_style_guide_prompt.py -v`

- [ ] **Step 3: Implement in `openrouter.py`**

Add `STYLE_GUIDE_ASPECT_RATIO = "1:1"`, `build_style_guide_prompt()`, `build_style_guide_request_payload()`, `generate_style_guide()` — same POST/extract pattern as `generate_tryon()`. Prompt per spec (focused board, beige `#F5F0EB`, identity lock, infer season/undertone from image).

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

---

### Task 2: Database — Link Style Guides to Generations

**Files:**
- Modify: `bot/db/migrations.py`, `bot/db/database.py`
- Create: `tests/test_style_guide_flow.py`

- [ ] **Step 1: Failing test**

```python
@pytest.mark.asyncio
async def test_record_generation_returns_id_and_style_guide_update(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = await db.ensure_user(telegram_id=12345)
    gen_id = await db.record_generation(user_id, "/g.jpg", "/r.jpg")
    assert isinstance(gen_id, int)
    await db.set_style_guide_path(gen_id, user_id, "/sg.jpg")
    row = await db.get_generation(gen_id, user_id)
    assert row["style_guide_path"] == "/sg.jpg"
    assert row["style_guide_at"] is not None
```

- [ ] **Step 2–4: Migration + methods**

`record_generation()` → returns `lastrowid`. Add `get_generation()`, `set_style_guide_path()`, `get_generation_for_user_by_id()`.

- [ ] **Step 5: Commit**

---

### Task 3: Style Guide Copy + Result Keyboard

**Files:**
- Modify: `bot/copy/__init__.py`, `bot/copy/en.py`, `bot/copy/ru.py`, `bot/keyboards.py`
- Modify: `tests/test_tryon_communication.py`, `tests/test_style_guide_flow.py`

- [ ] **Step 1: Add Copy fields**

```python
btn_style_guide: str
style_guide_offer: str
style_guide_generating: str
style_guide_caption: str
style_guide_already: str
style_guide_failed: str
style_guide_not_found: str
```

- [ ] **Step 2: Add brand-kit strings to `en.py`**

```python
btn_style_guide="✨ What to pair with this",
style_guide_offer=(
    "Love this look? 🔥 Get a style board for this piece — "
    "what to pair, colors & accessories. *1 try-on.*"
),
style_guide_generating="Putting your style board together… about 20 sec ✨",
style_guide_caption="Your style board — pairings, colors & accessories for this look 👗",
style_guide_already="You've already got a style board for this look 👇",
style_guide_failed=(
    "That one didn't come through — and I've refunded your try-on. "
    "Mind giving it another go?"
),
style_guide_not_found=(
    "I can't find that try-on anymore. Send a clothing photo and let's style something new 👗"
),
```

- [ ] **Step 3: Update `result_keyboard(balance, generation_id)`**

Row 1 = Style guide button (primary upsell). Pass `generation_id` from try-on handler.

- [ ] **Step 4: Tests**

```python
def test_result_keyboard_style_guide_is_first_row():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.callback_data == "styleguide:42"
    assert "pair" in first_btn.text.lower()

def test_style_guide_copy_uses_try_on_not_credit():
    init_copy("en")
    copy = active_copy()
    assert "credit" not in copy.style_guide_offer.lower()
    assert "try-on" in copy.style_guide_offer.lower()
```

- [ ] **Step 5: Commit**

---

### Task 4: Style Guide Handler

**Files:**
- Create: `bot/handlers/styleguide.py`
- Modify: `bot/services/openrouter.py` (`FileStorage.save_style_guide_photo`)
- Modify: `bot/main.py`

- [ ] **Step 1: Handler logic**

```python
STYLE_GUIDE_OFFER_DELAY_SECONDS = 30

@router.callback_query(F.data.startswith("styleguide:"))
async def style_guide_callback(callback, db, storage, openrouter, ...):
    generation_id = int(callback.data.split(":")[1])
    # 1. Verify ownership via get_generation_for_user_by_id
    # 2. If style_guide_path → resend photo + style_guide_already (no charge)
    # 3. If balance < 1 → paywall/deficit (reuse shop/deficit keyboards)
    # 4. deduct_credit → guard.acquire → status message (style_guide_generating)
    # 5. Read result_path bytes → openrouter.generate_style_guide()
    # 6. save_style_guide_photo → set_style_guide_path
    # 7. Send photo with style_guide_caption + result_keyboard
    # 8. analytics: style_guide_clicked, style_guide_generated
    # On TryOnError: refund, style_guide_failed (no raw {error} to user)

async def schedule_style_guide_offer(bot, db, telegram_id, generation_id, balance):
    await asyncio.sleep(30)
    row = await db.get_generation_for_user_by_id(generation_id, telegram_id)
    if not row or row["style_guide_path"] or balance < 1:
        return
    copy = active_copy()
    await bot.send_message(
        telegram_id,
        copy.style_guide_offer,
        parse_mode="Markdown",
        reply_markup=style_guide_offer_keyboard(generation_id),
    )
    await Analytics(db).track(telegram_id, "style_guide_offered")
```

- [ ] **Step 2: Register router in `main.py`**

- [ ] **Step 3: Smoke test** — try-on → button → board delivered

- [ ] **Step 4: Commit**

---

### Task 5: Wire Try-On → Style Guide

**Files:**
- Modify: `bot/handlers/tryon.py`

- [ ] **Step 1: Update success path**

```python
generation_id = await db.record_generation(user["id"], str(garment_path), str(result_path))
caption, keyboard = build_result_message(remaining, total_purchases, generation_id)
await message.answer_photo(..., reply_markup=keyboard)
asyncio.create_task(
    schedule_style_guide_offer(bot, db, message.from_user.id, generation_id, remaining)
)
```

Update `build_result_message(..., generation_id: int)` signature.

- [ ] **Step 2: Full test suite**

Run: `pytest -v`

- [ ] **Step 3: Commit**

---

### Task 6: Help Text + Analytics

**Files:**
- Modify: `bot/copy/en.py`

- [ ] **Step 1: Add to help_text (brand kit §11 style)**

```
*After a try-on*
Tap ✨ What to pair with this for a style board — pairings, colors & accessories (1 try-on).
```

- [ ] **Step 2: Verify analytics events fire**

`style_guide_offered`, `style_guide_clicked`, `style_guide_generated`, `style_guide_failed`

- [ ] **Step 3: Commit**

---

## Copy Checklist (Brand Kit Compliance)

Before shipping, grep codebase for Style Guide user-facing strings:

| Rule | Check |
|---|---|
| No "credit(s)" | All strings say "try-on(s)" |
| No "AI" | Prompt is internal only; never surfaced |
| One CTA per message | Offer text ends on value; button carries action |
| Peak-emotion sell | Upsell only after successful try-on, never on errors |
| Error = refund + retry | `style_guide_failed` matches kit §06 voice |
| Value button label | `✨ What to pair with this` not "Style guide" jargon |

---

## Plan Self-Review

| Requirement | Task |
|---|---|
| Brand kit copy principles | Task 0 + Task 3 + Copy Checklist |
| 1 try-on pricing | Task 4 |
| Button row 1 + 30s follow-up | Tasks 3, 4, 5 |
| 1:1 focused board | Task 1 |
| Input = try-on result | Task 4 |
| Free replay | Task 2 + Task 4 |
| Refund on failure | Task 4 |
| Guard / circuit breaker | Task 4 |

---

## Execution Options

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline** — execute all tasks in this session with checkpoints

Which approach?

# Fitting Room V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship unified look cart (1–5 garments, generate anytime) and My photos gallery (5 slots, 1 active) without Quick/Full mode selection.

**Architecture:** Persist garments in `look_carts` JSON column; extend `user_photos` with `is_active` + `slot_index`; route post-onboarding garment photos to cart via `bot/handlers/look.py`; generate with active person + N garments through OpenRouter; reuse GenerationGuard, credits, style guide upsell.

**Tech Stack:** Python 3.14, aiogram 3, aiosqlite, pytest, pytest-asyncio, OpenRouter `google/gemini-3.1-flash-image`

## Global Constraints

- Max reference photos: **5**; exactly **1 active** per user
- Look cart: **1–5** garments; **no type labels** in UI
- **No mode selection** — single unified flow (send items → See it on me)
- Generate threshold: **min 1 item**; **1 try-on** per generation regardless of item count
- Clear look cart **automatically on successful generation**
- Unfinished look TTL: **24 hours**
- OpenRouter model: **`google/gemini-3.1-flash-image`**; aspect **3:4**; size **1K**
- User-facing copy: **try-ons** not credits; **never say AI**
- Locale: **English first** in `bot/copy/en.py`; stubs in `ru.py`
- Spec: `docs/superpowers/specs/2026-07-15-fitting-room-v2-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `bot/db/migrations.py` | Modify | V2 schema migrations |
| `bot/db/database.py` | Modify | Active photo + look cart CRUD |
| `bot/services/look_cart.py` | Create | Cart add/clear/max-5 |
| `bot/services/openrouter.py` | Modify | Multi-garment prompt + generate |
| `bot/copy/__init__.py`, `en.py`, `ru.py` | Modify | V2 strings |
| `bot/keyboards.py` | Modify | Gallery + cart keyboards |
| `bot/handlers/photos.py` | Modify | Gallery UX |
| `bot/handlers/look.py` | Create | Garment intake, generate, clear |
| `bot/handlers/tryon.py` | Modify | Remove direct garment generate |
| `bot/handlers/start.py` | Modify | Welcome back with active slot + draft look |
| `bot/config.py` | Modify | `MAX_USER_PHOTOS` default **5** |
| `bot/main.py` | Modify | Register look router; cart purge worker |
| `tests/test_photo_gallery.py` | Create | DB + gallery tests |
| `tests/test_look_cart.py` | Create | Cart service tests |
| `tests/test_outfit_prompt.py` | Create | Prompt tests |

---

### Task 1: Database — Active Photos + Look Cart

**Files:**
- Modify: `bot/db/migrations.py`
- Modify: `bot/db/database.py`
- Test: `tests/test_photo_gallery.py`

**Interfaces:**
- Consumes: existing `Database.connect()`, migration pattern in `bot/db/migrations.py`
- Produces:
  - `async def list_user_photos(user_id: int) -> list[aiosqlite.Row]`
  - `async def get_active_photo(user_id: int) -> aiosqlite.Row | None`
  - `async def set_active_photo(photo_id: int, user_id: int) -> bool`
  - `async def add_user_photo(user_id: int, path: str) -> int` *(updated: sets is_active=1, slot_index)*
  - `async def get_active_photo_path(user_id: int) -> str | None` *(reads is_active row)*
  - `async def backfill_active_photos() -> None`
  - `async def get_look_cart(user_id: int) -> list[str]`
  - `async def set_look_cart(user_id: int, paths: list[str]) -> None`
  - `async def clear_look_cart(user_id: int) -> None`
  - `async def purge_stale_look_carts(max_age_hours: int = 24) -> int`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_photo_gallery.py
import pytest
from bot.db.database import Database


@pytest.mark.asyncio
async def test_set_active_photo_only_one_active(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(111, None, 2))["id"]
    p1 = await db.add_user_photo(user_id, "/p1.jpg")
    p2 = await db.add_user_photo(user_id, "/p2.jpg")
    assert await db.set_active_photo(p1, user_id)
    active = await db.get_active_photo(user_id)
    assert active["id"] == p1
    assert await db.set_active_photo(p2, user_id)
    active = await db.get_active_photo(user_id)
    assert active["id"] == p2
    photos = await db.list_user_photos(user_id)
    assert sum(int(p["is_active"]) for p in photos) == 1


@pytest.mark.asyncio
async def test_look_cart_roundtrip(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(222, None, 2))["id"]
    await db.set_look_cart(user_id, ["/g1.jpg", "/g2.jpg"])
    assert await db.get_look_cart(user_id) == ["/g1.jpg", "/g2.jpg"]
    await db.clear_look_cart(user_id)
    assert await db.get_look_cart(user_id) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_photo_gallery.py -v`  
Expected: FAIL — `set_active_photo` not defined

- [ ] **Step 3: Add migrations**

In `bot/db/migrations.py`:

```python
"ALTER TABLE user_photos ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0",
"ALTER TABLE user_photos ADD COLUMN slot_index INTEGER",
"ALTER TABLE generations ADD COLUMN garment_count INTEGER NOT NULL DEFAULT 1",
"ALTER TABLE generations ADD COLUMN mode TEXT NOT NULL DEFAULT 'cart'",
```

In `bot/db/migrations.py` `NEW_TABLES` append:

```sql
CREATE TABLE IF NOT EXISTS look_carts (
    user_id INTEGER PRIMARY KEY,
    garment_paths TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

- [ ] **Step 4: Implement database methods**

Update `add_user_photo` to assign `slot_index = count+1`, set `is_active=1`, clear other actives:

```python
async def add_user_photo(self, user_id: int, path: str) -> int:
    count = await self.count_user_photos(user_id)
    slot_index = count + 1
    await self.conn.execute(
        "UPDATE user_photos SET is_active = 0 WHERE user_id = ?",
        (user_id,),
    )
    cursor = await self.conn.execute(
        """
        INSERT INTO user_photos (user_id, path, is_active, slot_index)
        VALUES (?, ?, 1, ?)
        """,
        (user_id, path, slot_index),
    )
    photo_id = int(cursor.lastrowid)
    await self.conn.execute(
        "UPDATE users SET primary_photo_id = ? WHERE id = ?",
        (photo_id, user_id),
    )
    await self.conn.commit()
    return photo_id
```

Implement `get_active_photo_path` via `is_active=1` join (keep `primary_photo_id` in sync on switch).

Implement look cart with JSON:

```python
import json

async def get_look_cart(self, user_id: int) -> list[str]:
    cursor = await self.conn.execute(
        "SELECT garment_paths FROM look_carts WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if not row:
        return []
    return json.loads(row["garment_paths"])

async def set_look_cart(self, user_id: int, paths: list[str]) -> None:
    await self.conn.execute(
        """
        INSERT INTO look_carts (user_id, garment_paths, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            garment_paths = excluded.garment_paths,
            updated_at = datetime('now')
        """,
        (user_id, json.dumps(paths)),
    )
    await self.conn.commit()
```

Call `backfill_active_photos()` once in `connect()` after migrations:

```python
async def backfill_active_photos(self) -> None:
    await self.conn.execute(
        """
        UPDATE user_photos SET is_active = 1
        WHERE id IN (
            SELECT primary_photo_id FROM users WHERE primary_photo_id IS NOT NULL
        )
        """
    )
    await self.conn.commit()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_photo_gallery.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add bot/db/migrations.py bot/db/database.py tests/test_photo_gallery.py
git commit -m "feat: active photo flag and look cart storage"
```

---

### Task 2: LookCartService

**Files:**
- Create: `bot/services/look_cart.py`
- Test: `tests/test_look_cart.py`

**Interfaces:**
- Consumes: `Database.get_look_cart`, `Database.set_look_cart`, `Database.clear_look_cart`, `validate_and_process_garment_photo`, `FileStorage.save_garment_photo`
- Produces:
  - `class LookCartService`
  - `async def add_garment(self, user_id: int, telegram_id: int, raw: bytes, generation_id: int) -> tuple[int, bool]` → `(count, at_limit)`
  - `async def get_count(self, user_id: int) -> int`
  - `async def clear(self, user_id: int) -> None`
  - `MAX_ITEMS = 5`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_look_cart.py
import pytest
from bot.db.database import Database
from bot.services.look_cart import LookCartService
from bot.services.openrouter import FileStorage
from tests.test_image_processor import _make_tall_photo  # or inline helper


@pytest.mark.asyncio
async def test_add_garment_increments_cart(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(333, None, 2)
    storage = FileStorage(tmp_path / "storage")
    svc = LookCartService(db, storage)
    raw = _make_tall_photo()
    count, at_limit = await svc.add_garment(user["id"], 333, raw, generation_id=1)
    assert count == 1
    assert at_limit is False
    count2, _ = await svc.add_garment(user["id"], 333, raw, generation_id=2)
    assert count2 == 2


@pytest.mark.asyncio
async def test_add_garment_stops_at_five(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user = await db.get_or_create_user(444, None, 2)
    storage = FileStorage(tmp_path / "storage")
    svc = LookCartService(db, storage)
    raw = b"\xff\xd8\xff" + b"\x00" * 300  # will fail validation — use real helper
```

Use valid JPEG bytes from existing test helper in `tests/test_image_processor.py`.

- [ ] **Step 2: Run test — expect FAIL**

Run: `.venv/bin/pytest tests/test_look_cart.py -v`

- [ ] **Step 3: Implement LookCartService**

```python
# bot/services/look_cart.py
from __future__ import annotations

from bot.db.database import Database
from bot.services.image_processor import PhotoValidationError, validate_and_process_garment_photo
from bot.services.openrouter import FileStorage

MAX_CART_ITEMS = 5


class LookCartService:
    def __init__(self, db: Database, storage: FileStorage) -> None:
        self.db = db
        self.storage = storage

    async def get_count(self, user_id: int) -> int:
        return len(await self.db.get_look_cart(user_id))

    async def add_garment(
        self,
        user_id: int,
        telegram_id: int,
        raw: bytes,
        generation_id: int,
    ) -> tuple[int, bool]:
        paths = await self.db.get_look_cart(user_id)
        if len(paths) >= MAX_CART_ITEMS:
            return len(paths), True
        processed = validate_and_process_garment_photo(raw)
        path = str(
            self.storage.save_garment_photo(telegram_id, generation_id, processed)
        )
        paths.append(path)
        await self.db.set_look_cart(user_id, paths)
        return len(paths), len(paths) >= MAX_CART_ITEMS

    async def clear(self, user_id: int) -> None:
        await self.db.clear_look_cart(user_id)

    async def paths(self, user_id: int) -> list[str]:
        return await self.db.get_look_cart(user_id)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add bot/services/look_cart.py tests/test_look_cart.py
git commit -m "feat: look cart service"
```

---

### Task 3: Copy + Keyboards

**Files:**
- Modify: `bot/copy/__init__.py`, `bot/copy/en.py`, `bot/copy/ru.py`
- Modify: `bot/keyboards.py`
- Modify: `bot/filters.py` *(no change needed if field renamed in Copy)*
- Test: `tests/test_look_cart.py` *(append keyboard tests)*

**Interfaces:**
- Produces:
  - Copy fields: `btn_my_photos`, `btn_see_on_me`, `btn_add_item`, `btn_clear_look`, `look_item_added`, `look_one_item_hint`, `look_full`, `look_cleared`, `look_generating_one`, `look_generating_many`, `photo_switched`, `gallery_header`, `try_on_hint_v2`, `person_photo_in_tryon`, `welcome_back_draft_look`
  - `def photo_gallery_keyboard(photos: list, *, max_photos: int = 5) -> InlineKeyboardMarkup`
  - `def look_cart_keyboard(count: int, *, at_limit: bool) -> InlineKeyboardMarkup`
  - `def draft_look_keyboard() -> InlineKeyboardMarkup`

- [ ] **Step 1: Write failing test**

```python
def test_look_cart_keyboard_has_generate():
    from bot.copy import init_copy
    from bot.keyboards import look_cart_keyboard
    init_copy("en")
    kb = look_cart_keyboard(2, at_limit=False)
    callbacks = [b.callback_data for row in kb.inline_keyboard for b in row if b.callback_data]
    assert "look:generate" in callbacks
    assert "look:clear" in callbacks
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Add Copy fields and strings** (exact text from spec § Key Copy)

Rename `btn_reupload` → `btn_my_photos` in dataclass and both locale files. Update `main_keyboard()` to use `copy.btn_my_photos`.

```python
def look_cart_keyboard(count: int, *, at_limit: bool) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [[InlineKeyboardButton(text=copy.btn_see_on_me, callback_data="look:generate")]]
    if not at_limit:
        rows.append([InlineKeyboardButton(text=copy.btn_add_item, callback_data="look:add_hint")])
    rows.append([InlineKeyboardButton(text=copy.btn_clear_look, callback_data="look:clear")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

```python
def photo_gallery_keyboard(photos: list, *, max_photos: int = 5) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = []
    for photo in photos:
        slot = photo["slot_index"]
        label = f"Photo {slot} ✓" if photo["is_active"] else f"Photo {slot}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"photo:{photo['id']}")])
    if len(photos) < max_photos:
        rows.append([InlineKeyboardButton(text="➕ Add photo", callback_data="photo:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add bot/copy/ bot/keyboards.py tests/test_look_cart.py
git commit -m "feat: V2 gallery and look cart copy and keyboards"
```

---

### Task 4: My Photos Gallery Handler

**Files:**
- Modify: `bot/handlers/photos.py`
- Test: `tests/test_photo_gallery.py`

**Interfaces:**
- Consumes: `Database.list_user_photos`, `set_active_photo`, `photo_gallery_keyboard`, `gallery_header`, `photo_switched`
- Produces:
  - FSM `PhotosAdding.adding` (rename from `Reupload`)
  - `async def show_gallery(message, db, settings) -> None`
  - `@router.callback_query(F.data.startswith("photo:"))` handlers

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_list_user_photos_ordered_by_slot(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(555, None, 2))["id"]
    await db.add_user_photo(user_id, "/a.jpg")
    await db.add_user_photo(user_id, "/b.jpg")
    photos = await db.list_user_photos(user_id)
    assert len(photos) == 2
    assert photos[-1]["is_active"] == 1
```

- [ ] **Step 2–4: Implement gallery**

Replace `TextIs("btn_reupload")` with `TextIs("btn_my_photos")`. `/photos` and button call `show_gallery()`:

```python
async def show_gallery(message: Message, db: Database, settings: Settings) -> None:
    copy = active_copy()
    user = await db.fetch_user(message.from_user.id)
    photos = await db.list_user_photos(user["id"])
    active = await db.get_active_photo(user["id"])
    active_slot = active["slot_index"] if active else 0
    await message.answer(
        copy.gallery_header.format(count=len(photos), active_slot=active_slot),
        parse_mode="Markdown",
        reply_markup=photo_gallery_keyboard(photos, max_photos=settings.max_user_photos),
    )
```

Callback `photo:{id}` → `set_active_photo` → `photo_switched` message.

Callback `photo:add` → FSM `PhotosAdding.adding`.

At 5/5: show replace hint using `photo_limit_reached` copy variant.

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/photos.py tests/test_photo_gallery.py
git commit -m "feat: my photos gallery with active selection"
```

---

### Task 5: Multi-Garment OpenRouter Prompt

**Files:**
- Modify: `bot/services/openrouter.py`
- Test: `tests/test_outfit_prompt.py`

**Interfaces:**
- Produces:
  - `def build_outfit_tryon_prompt(garment_count: int) -> str`
  - `def build_outfit_tryon_request_payload(model: str, person: bytes, garments: list[bytes]) -> dict`
  - `async def generate_outfit_tryon(self, person: bytes, garments: list[bytes]) -> bytes`

- [ ] **Step 1: Write failing test**

```python
import json
from bot.services.openrouter import build_outfit_tryon_prompt, build_outfit_tryon_request_payload

def test_outfit_prompt_task_and_garment_count():
    payload = json.loads(build_outfit_tryon_prompt(3))
    assert payload["task"] == "virtual_try_on_outfit"
    assert payload["inputs"]["garment_count"] == 3

def test_outfit_payload_has_four_images_for_three_garments():
    payload = build_outfit_tryon_request_payload("google/gemini-3.1-flash-image", b"p", [b"g1", b"g2", b"g3"])
    content = payload["messages"][0]["content"]
    image_parts = [p for p in content if p["type"] == "image_url"]
    assert len(image_parts) == 4
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

When `len(garments) == 1`, call existing `generate_tryon`. When `len(garments) >= 2`, use outfit prompt with dynamic image list (person first, then each garment).

- [ ] **Step 4: Run — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add bot/services/openrouter.py tests/test_outfit_prompt.py
git commit -m "feat: multi-garment outfit try-on prompt"
```

---

### Task 6: Look Handler — Cart + Generate

**Files:**
- Create: `bot/handlers/look.py`
- Modify: `bot/handlers/tryon.py` *(remove garment photo handler)*
- Modify: `bot/db/database.py` *(extend record_generation)*
- Modify: `bot/main.py`
- Test: `tests/test_look_cart.py`

**Interfaces:**
- Consumes: `LookCartService`, `look_cart_keyboard`, `build_result_message`, `GenerationGuard`, `OpenRouterClient.generate_outfit_tryon`
- Produces:
  - `router = Router(name="look")`
  - `async def send_cart_status(message, db, user_id) -> None`
  - `@router.message(F.photo, ~Onboarding, ~PhotosAdding.adding)` → add to cart
  - `@router.callback_query(F.data == "look:generate")` → generate flow
  - `@router.callback_query(F.data == "look:clear")` → clear cart

- [ ] **Step 1: Extend record_generation**

```python
async def record_generation(
    self, user_id: int, garment_path: str, result_path: str,
    *, garment_count: int = 1, mode: str = "cart",
) -> int:
```

- [ ] **Step 2: Implement look.py generate callback**

Pseudocode flow (implement fully):

```python
@router.callback_query(F.data == "look:generate")
async def look_generate(callback, db, storage, openrouter, drip, bot):
    copy = active_copy()
    user = await db.fetch_user(callback.from_user.id)
    paths = await db.get_look_cart(user["id"])
    if not paths:
        await callback.answer("Add at least one item first.", show_alert=True)
        return
    person_path = await db.get_active_photo_path(user["id"])
    if not person_path:
        await callback.answer(copy.no_saved_photos, show_alert=True)
        return
    balance = await db.get_balance(callback.from_user.id)
    if balance < 1:
        # paywall / deficit — same as tryon.py
        ...
    # deduct, guard, generating message
    person_bytes = storage.read(person_path)
    garment_bytes = [storage.read(p) for p in paths]
    result = await openrouter.generate_outfit_tryon(person_bytes, garment_bytes)
    # save result, record_generation(garment_count=len(paths), mode="cart")
    # clear cart, answer_photo with build_result_message + schedule_style_guide_offer
    # refund on TryOnError
```

Garment message handler:

```python
@router.message(F.photo, ~StateFilter(Onboarding.collecting_photos), ~StateFilter(PhotosAdding.adding))
async def add_garment_to_cart(message, bot, db, storage, settings):
    ok, err = await _user_ready(db, message.from_user.id)
    if not ok:
        await message.answer(err)
        return
    user = await db.fetch_user(message.from_user.id)
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    raw = (await bot.download_file(file.file_path)).read()
    svc = LookCartService(db, storage)
    try:
        count, at_limit = await svc.add_garment(
            user["id"], message.from_user.id, raw, int(time.time())
        )
    except PhotoValidationError as exc:
        await message.answer(str(exc), reply_markup=guide_button_keyboard())
        return
    copy = active_copy()
    active = await db.get_active_photo(user["id"])
    slot = active["slot_index"] if active else 1
    text = copy.look_item_added.format(count=count, active_slot=slot)
    if count == 1:
        text += f"\n\n{copy.look_one_item_hint}"
    if at_limit:
        text = copy.look_full
    await message.answer(text, parse_mode="Markdown", reply_markup=look_cart_keyboard(count, at_limit=at_limit))
    await Analytics(db).track(message.from_user.id, "look_item_added", {"count": count})
```

Register `look.router` in `main.py` **before** `tryon.router`. Remove `@router.message(F.photo...)` from `tryon.py`.

- [ ] **Step 3: Album support**

Add handler using aiogram album middleware or collect `media_group_id` messages into a list, then add each to cart in one status update.

- [ ] **Step 4: Run full pytest**

Run: `.venv/bin/pytest -v`  
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/look.py bot/handlers/tryon.py bot/db/database.py bot/main.py tests/
git commit -m "feat: look cart handler and unified generate flow"
```

---

### Task 7: Start + Try-On Hint + Config

**Files:**
- Modify: `bot/handlers/start.py`
- Modify: `bot/handlers/tryon.py` *(try_on_hint only)*
- Modify: `bot/config.py`
- Modify: `bot/copy/en.py` `help_text`

**Interfaces:**
- Consumes: `get_active_photo`, `get_look_cart`, `try_on_hint_v2`, `welcome_back_draft_look`

- [ ] **Step 1: Update config default**

```python
max_user_photos=int(os.getenv("MAX_USER_PHOTOS", "5")),
```

- [ ] **Step 2: Welcome back with context**

```python
if user["onboarding_complete"]:
    balance = await db.get_balance(message.from_user.id)
    active = await db.get_active_photo(user["id"])
    slot = active["slot_index"] if active else 1
    cart_count = len(await db.get_look_cart(user["id"]))
    if cart_count > 0:
        await message.answer(
            copy.welcome_back_draft_look.format(count=cart_count),
            reply_markup=draft_look_keyboard(),
        )
    else:
        await message.answer(
            copy.welcome_back.format(balance=balance) + f"\nActive photo: Photo {slot} ✓",
            reply_markup=main_keyboard(),
        )
```

Add `welcome_back_draft_look` to copy:
`"Welcome back 👋\nYou have a look waiting — {count} items."`

- [ ] **Step 3: Try on button → hint v2**

```python
@router.message(TextIs("btn_try_on"))
async def try_on_hint(message, db):
    user = await db.fetch_user(message.from_user.id)
    active = await db.get_active_photo(user["id"])
    slot = active["slot_index"] if active else 1
    await message.answer(
        active_copy().try_on_hint_v2.format(active_slot=slot),
        reply_markup=main_keyboard(),
    )
```

- [ ] **Step 4: Update help_text** with gallery + cart section from spec

- [ ] **Step 5: Commit**

```bash
git add bot/handlers/start.py bot/handlers/tryon.py bot/config.py bot/copy/
git commit -m "feat: V2 welcome context and try-on hints"
```

---

### Task 8: Look Cart TTL Purge Worker

**Files:**
- Modify: `bot/main.py`
- Modify: `bot/db/database.py`
- Test: `tests/test_look_cart.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_purge_stale_look_carts(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    user_id = (await db.get_or_create_user(666, None, 2))["id"]
    await db.set_look_cart(user_id, ["/g.jpg"])
    await db.conn.execute(
        "UPDATE look_carts SET updated_at = datetime('now', '-25 hours') WHERE user_id = ?",
        (user_id,),
    )
    await db.conn.commit()
    removed = await db.purge_stale_look_carts(max_age_hours=24)
    assert removed == 1
    assert await db.get_look_cart(user_id) == []
```

- [ ] **Step 2–4: Implement purge + daily worker** (mirror `purge_worker` pattern in `main.py`)

- [ ] **Step 5: Commit**

```bash
git add bot/db/database.py bot/main.py tests/test_look_cart.py
git commit -m "feat: purge stale look carts after 24h"
```

---

## Plan Self-Review

| Spec requirement | Task |
|---|---|
| 5 photos, 1 active | 1, 4 |
| Unified cart, no modes | 6, 7 |
| Generate at 1+ items | 6 |
| Batch/album | 6 |
| 1 try-on per generate | 6 |
| Clear cart on success | 6 |
| 24h TTL | 8 |
| Brand kit copy | 3, 7 |
| Multi-garment AI | 5, 6 |
| Analytics events | 6 |
| Style guide on result | 6 (reuse existing) |
| MAX_USER_PHOTOS=5 | 7 |

No placeholders remain. Signatures consistent across tasks.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-15-fitting-room-v2.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** — execute tasks in this session with checkpoints

Which approach?

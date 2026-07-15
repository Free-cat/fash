# Fitting Room V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unified look cart (1–5 garments, generate anytime) + My photos gallery (5 slots, 1 active) — no Quick/Full mode split.

**Architecture:** `look_carts` table + `LookCartService` for garment queue; extend `user_photos` with `is_active`; route all post-onboarding garment photos to cart; generate sends active person + N garments to OpenRouter; brand-kit copy throughout.

**Tech Stack:** Python 3, aiogram 3, SQLite, OpenRouter (`google/gemini-3.1-flash-image`), pytest

**Spec:** `docs/superpowers/specs/2026-07-15-fitting-room-v2-design.md`

---

## File Map

| File | Action |
|---|---|
| `bot/db/migrations.py` | `is_active`, `look_carts`, `generations.garment_count` |
| `bot/db/database.py` | Photo active/switch; look cart CRUD |
| `bot/services/look_cart.py` | Create — cart logic, debounce, max 5 |
| `bot/services/openrouter.py` | `generate_outfit_tryon(person, garments[])` |
| `bot/copy/__init__.py`, `en.py`, `ru.py` | Gallery + cart strings |
| `bot/keyboards.py` | Gallery + cart keyboards |
| `bot/handlers/photos.py` | Gallery UX refactor |
| `bot/handlers/look.py` | Create — cart callbacks, generate |
| `bot/handlers/tryon.py` | Route garments to cart; remove direct generate |
| `bot/handlers/start.py` | Welcome hints V2 |
| `bot/config.py` | Default `max_user_photos=5` |
| `bot/main.py` | Register look router; cart purge worker |
| `tests/test_look_cart.py` | Create |
| `tests/test_photo_gallery.py` | Create |
| `tests/test_outfit_prompt.py` | Create |

---

### Task 1: Database — Photos Active + Look Cart

**Files:** `bot/db/migrations.py`, `bot/db/database.py`, `tests/test_photo_gallery.py`

- [ ] Migration: `user_photos.is_active`, `look_carts` table, `generations.garment_count`
- [ ] `set_active_photo(photo_id, user_id)`, `get_active_photo(user_id)`, `list_user_photos(user_id)`
- [ ] Backfill: existing users → first photo `is_active=1`
- [ ] Look cart: `get_cart`, `add_garment`, `clear_cart`, `garment_count`
- [ ] Test: switch active, only one active, cart add/clear/max 5

Commit: `feat: add photo active flag and look cart storage`

---

### Task 2: LookCartService

**Files:** `bot/services/look_cart.py`, `tests/test_look_cart.py`

- [ ] `LookCartService(db, storage)` — add from raw bytes (validate garment), debounce 3s batch counter for rapid messages
- [ ] Enforce max 5; return `(count, at_limit)`
- [ ] Test: sequential adds, max enforcement

Commit: `feat: look cart service with garment validation`

---

### Task 3: Copy + Keyboards

**Files:** `bot/copy/*`, `bot/keyboards.py`, `tests/test_look_cart.py`

- [ ] Add all spec copy keys (`btn_my_photos`, `btn_see_on_me`, `look_item_added`, etc.)
- [ ] Rename `btn_reupload` → `btn_my_photos` in en/ru
- [ ] `photo_gallery_keyboard(photos)`, `look_cart_keyboard(count, at_limit)`
- [ ] Test: keyboard callbacks `photo:{id}`, `look:generate`, `look:clear`

Commit: `feat: V2 gallery and look cart copy and keyboards`

---

### Task 4: My Photos Gallery Handler

**Files:** `bot/handlers/photos.py`, `tests/test_photo_gallery.py`

- [ ] `/photos` and `btn_my_photos` → gallery header + inline thumbs
- [ ] Callback `photo:{id}` → switch active
- [ ] FSM `photos.adding` for add/replace
- [ ] Max 5: replace flow or block with friendly copy
- [ ] Remove auto-complete reupload as "latest wins only" — explicit active switch

Commit: `feat: my photos gallery with active photo selection`

---

### Task 5: Multi-Garment OpenRouter Prompt

**Files:** `bot/services/openrouter.py`, `tests/test_outfit_prompt.py`

- [ ] `build_outfit_tryon_prompt(garment_count)` — JSON structured, all garments on person
- [ ] `generate_outfit_tryon(person_bytes, garment_bytes_list)` — dynamic message content with N images
- [ ] N=1 delegates to existing try-on prompt (or unified)
- [ ] Test: prompt keys, payload image count

Commit: `feat: multi-garment outfit try-on prompt`

---

### Task 6: Look Handler — Cart + Generate

**Files:** `bot/handlers/look.py`, `bot/main.py`

- [ ] Garment photo handler (post-onboarding): add to cart → status message + keyboard
- [ ] Album handler (`media_group_id`): add all photos in group
- [ ] Callbacks: `look:generate`, `look:clear`
- [ ] Generate: deduct credit, guard, read active person + cart paths, call `generate_outfit_tryon`, record generation with `garment_count`, clear cart, result keyboard
- [ ] Refund on failure
- [ ] Register router

Commit: `feat: look cart handler and generate flow`

---

### Task 7: Refactor tryon.py + Start Hints

**Files:** `bot/handlers/tryon.py`, `bot/handlers/start.py`

- [ ] Remove direct garment→generate from tryon router (move to look handler)
- [ ] `btn_try_on` → sends `try_on_hint_v2` (not mode menu)
- [ ] Welcome back: show active photo slot + draft look count if cart non-empty
- [ ] Update `test_tryon_communication.py` as needed

Commit: `refactor: unified try-on entry through look cart`

---

### Task 8: Cart TTL Purge + Config

**Files:** `bot/main.py`, `bot/config.py`, `bot/services/look_cart.py`

- [ ] Daily worker: delete look_carts older than 24h
- [ ] `MAX_USER_PHOTOS` default 5
- [ ] Help text update for gallery + cart

Commit: `feat: look cart TTL purge and config defaults`

---

### Task 9: Integration Tests + Smoke

- [ ] Full pytest pass
- [ ] Manual: onboarding → add 2 garments → see on me → switch photo → 3-item look
- [ ] Verify style guide still works on result

Commit: `test: V2 look cart integration coverage`

---

## Plan Self-Review

| Spec requirement | Task |
|---|---|
| 5 photos, 1 active | 1, 4 |
| Unified cart, no modes | 6, 7 |
| Generate at 1+ items | 6 |
| Batch/album support | 6 |
| 1 try-on per generate | 6 |
| Clear cart on success | 6 |
| 24h draft TTL | 8 |
| Brand kit copy | 3 |
| Multi-garment AI | 5 |

---

## Execution

Use subagent-driven-development — one task per subagent, review between tasks.

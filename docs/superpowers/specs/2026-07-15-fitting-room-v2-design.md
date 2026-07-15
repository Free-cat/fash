# Fitting Room V2 — Person Gallery & Look Cart

**Date:** 2026-07-15  
**Status:** Approved  
**Locale:** English first (`bot/copy/en.py`)  
**Depends on:** V1 try-on, style guide upsell, brand kit copy principles  
**Supersedes:** Multi-mode Quick/Full look split (rejected — unified cart instead)

## Goal

Increase product value and generation quality by giving users:
1. **My photos** — up to 5 reference photos of themselves, one **active** at a time
2. **Look cart** — accumulate 1–5 garment photos, generate **at any time** (1 try-on per generation)
3. **Unified try-on flow** — no mode selection; send item(s) → add more or generate

AI input remains: **active person photo + N garment images** (order-agnostic).

## Product Decisions (Approved)

| Decision | Choice |
|---|---|
| People | Only the account owner (no family/partner profiles) |
| Reference photos | Max **5**, exactly **1 active** for try-on |
| Garment collection | **Look cart**, 1–5 items, no type labels (AI infers) |
| Mode selection | **None** — single unified flow |
| Generate threshold | **Min 1 item** — generate anytime |
| Batch upload | **Yes** — album or rapid sequential photos all add to cart |
| Pricing | **1 try-on** per generation (1–5 items same price) |
| After result | **Clear look cart** automatically |
| Draft persistence | Unfinished look TTL **24 hours** |

## Copy Principles (Brand Kit)

1. Value-language: **try-ons**, never credits in user-facing copy
2. One clear next action per message; secondary actions in buttons
3. Always surface context: active photo, item count, balance
4. Never say "AI" — fitting room / styling / see it on you
5. Errors: refund try-on + one recovery step

## Mental Model

| Entity | User-facing name | Meaning |
|---|---|---|
| Active photo | "Photo N ✓" / "Using Photo 2 ✓" | The person reference used for generation |
| Look cart | "Your look · N items" | Garments queued before generate |
| Try-on | "See it on me" | One generation consuming 1 try-on |

## User Flows

### Flow 1 — Onboarding (updated)

```
/start → demo image
→ welcome: one full-body photo opens fitting room, 2 free try-ons
→ user sends person photo
→ "Fitting room is open 🎉" + privacy note
→ inline: [👗 Send a clothing photo] (hint only — any garment photo starts cart)
```

Onboarding completes after **1 person photo** (unchanged).

### Flow 2 — My photos gallery

**Trigger:** `📷 My photos` / `/photos`

```
*My photos* (2/5)
Active for try-ons: Photo 2 ✓

Tap a photo to make it active.
Send a new photo to add one (max 5).

Inline: [Photo 1] [Photo 2 ✓] [Photo 3] [➕ Add photo]
```

**Switch active:** callback `photo:{id}` → confirm "Photo N is now active 👍"

**Add photo:** FSM `photos_add` → user sends person photo → added, set active, show count

**At 5/5:** offer switch or replace oldest via `photo:replace:{id}`

**Person vs garment detection:** person photos in gallery flow only; garment photos rejected with friendly redirect to try-on.

### Flow 3 — Unified try-on (look cart)

**Entry:** user sends garment photo(s) anytime after onboarding (no mode menu).

**Single photo:**
```
Got it — 1 item 👗
Using Photo 2 ✓ · 1 try-on when you're ready

[✨ See it on me]
[➕ Add another item]
[🗑 Clear look]
```

**Multiple photos (album or rapid send within 3s debounce):**
```
Got it — 3 items in your look 👗
Using Photo 2 ✓ · 1 try-on when you're ready

[✨ See it on me]
[➕ Add more items]
[🗑 Clear look]
```

**At 5 items max:**
```
Look full — 5 items 🔥
[✨ See it on me]
[🗑 Clear look]
```

**Generate:** callback `look:generate`
- Deduct 1 try-on
- Status: "Putting it on you…" (1 item) / "Putting your look on you… about 20 sec ✨" (2+)
- OpenRouter: active person + all cart garment images
- Result caption + existing result keyboard (style guide, try another, share)
- **Clear cart** on success
- Refund on failure

**Clear:** callback `look:clear` → reset cart, confirm message

**Add while cart exists:** new garment photos append (never replace silently)

### Flow 4 — Returning user

**Balance > 0, no draft:**
```
Welcome back 👋
3 try-ons ready · Active photo: Photo 2 ✓
```

**Unfinished look (within 24h):**
```
Welcome back 👋
You have a look waiting — 2 items.

[✨ See it on me] [➕ Add more] [🗑 Clear]
```

**Balance = 0:** existing paywall copy (brand kit)

### Flow 5 — Wrong photo type

| Sent | Context | Response |
|---|---|---|
| Person photo | Not in photos_add / onboarding | "Looks like you — add to My photos?" [📷 Add to gallery] |
| Garment | photos_add FSM | "Send a full-body photo of yourself for My photos 📷" |
| Garment | onboarding | N/A — onboarding accepts person only via state filter |

## Reply Keyboard

```
👗 Try on          |  ⭐ My try-ons
📷 My photos       |  ⭐ Buy try-ons
❓ Help
```

`👗 Try on` sends hint message (not a mode picker):
```
Send clothing photos — one or several 👗
I'll put them on you using Photo 2 ✓
Add items, then tap See it on me · 1 try-on
```

## FSM States

| State | Accepts | Purpose |
|---|---|---|
| `idle` (default) | garments → cart; commands | Main loop |
| `onboarding.collecting_photos` | person photos | First setup |
| `photos.adding` | person photos | Gallery add/replace |
| `generating` (lock via GenerationGuard) | nothing | Concurrent block |

No separate `building_look` state — cart lives in DB/session while `idle`.

## Data Model

### `user_photos` (extend)

```sql
ALTER TABLE user_photos ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0;
ALTER TABLE user_photos ADD COLUMN slot_index INTEGER;  -- 1-5 display order
```

- Exactly one `is_active=1` per user
- On add: new photo becomes active unless user switched manually
- `set_active_photo(photo_id, user_id)` clears others then sets one

### `look_carts` (new)

```sql
CREATE TABLE look_carts (
    user_id INTEGER PRIMARY KEY,
    garment_paths TEXT NOT NULL,  -- JSON array of paths, max 5
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

- Garment paths stored after `validate_and_process_garment_photo`
- TTL: purge rows where `updated_at < now - 24 hours` (daily worker)

### `generations` (extend)

```sql
ALTER TABLE generations ADD COLUMN garment_count INTEGER NOT NULL DEFAULT 1;
ALTER TABLE generations ADD COLUMN mode TEXT NOT NULL DEFAULT 'cart';
```

`mode` values: `cart` (V2 unified), `single` (legacy rows)

## AI — Multi-Garment Prompt

New `build_outfit_tryon_prompt(garment_count: int)` or extend existing prompt:

- **Task:** `virtual_try_on_outfit`
- **Inputs:** image_1 = active person; images 2..N = all cart garments
- **Goal:** Dress person in ALL garments as one cohesive outfit
- **Garment rules:** infer roles (top/bottom/outerwear/shoes); no duplicate layers unless provided
- **Identity lock:** same as V1 try-on
- **Framing:** full body 3:4, head to toe
- **Config:** same model `google/gemini-3.1-flash-image`, aspect 3:4, 1K

Single-item cart uses existing try-on prompt (or unified prompt with N=1).

## Architecture

| Component | Responsibility |
|---|---|
| `bot/handlers/photos.py` | Gallery UI, active switch, add/replace |
| `bot/handlers/look.py` | Cart add, clear, generate callback |
| `bot/handlers/tryon.py` | Refactor: garment messages route to look cart; generate delegates to look handler |
| `bot/services/look_cart.py` | Cart CRUD, debounce batch adds, max 5 enforcement |
| `bot/services/openrouter.py` | `generate_outfit_tryon(person, garments[])` |
| `bot/keyboards.py` | `look_cart_keyboard(count)`, `photo_gallery_keyboard(photos)` |
| `bot/copy/en.py` | All new strings (gallery, cart, hints) |

## Key Copy (English Draft)

| Key | Text |
|---|---|
| `btn_my_photos` | `📷 My photos` |
| `btn_see_on_me` | `✨ See it on me` |
| `btn_add_item` | `➕ Add another item` |
| `btn_clear_look` | `🗑 Clear look` |
| `look_item_added` | `Got it — {count} item(s) in your look 👗\nUsing Photo {active_slot} ✓ · 1 try-on when you're ready` |
| `look_one_item_hint` | `Add more for a full look, or see it on you now.` |
| `look_full` | `Look full — 5 items 🔥` |
| `look_cleared` | `Look cleared — send clothing photos when you're ready 👗` |
| `look_generating_one` | `Putting it on you… about 15 sec ✨` |
| `look_generating_many` | `Putting your look on you… about 20 sec ✨` |
| `photo_switched` | `Photo {slot} is now your active photo 👍` |
| `gallery_header` | `*My photos* ({count}/5)\nActive for try-ons: Photo {active_slot} ✓` |
| `try_on_hint_v2` | `Send clothing photos — one or several 👗\nUsing Photo {active_slot} ✓ · add items, then See it on me · 1 try-on` |
| `person_photo_in_tryon` | `Looks like a photo of you — add it to My photos?` |

## Analytics Events

| Event | When |
|---|---|
| `photo_added` | Gallery add |
| `photo_switched` | Active changed |
| `look_item_added` | Garment added to cart |
| `look_cleared` | User cleared cart |
| `look_generated` | Success ({garment_count}) |
| `look_failed` | API error + refund |

## Error Handling

| Case | Behavior |
|---|---|
| 0 try-ons | Paywall / deficit (unchanged) |
| 0 garments on generate | Should not happen (button hidden) |
| >5 items | Reject with look_full message |
| No active photo | Block generate → redirect to My photos |
| Concurrent generation | Existing concurrent message |
| API failure | Refund 1 try-on, friendly error |

## Out of Scope (V2)

- Other people profiles (partner/child)
- Garment type labels in UI
- Single flat-lay outfit photo parsing
- Keep look cart after result (always clear on success)
- Pin status message in chat
- Full brand kit rollout for all V1 strings (separate task)

## Migration Notes

- Existing users: first photo in `user_photos` → set `is_active=1`
- `MAX_USER_PHOTOS` env default: **5** (was 3)
- Rename reply button `btn_reupload` → `btn_my_photos` in copy

## Success Criteria

1. User manages up to 5 photos with visible active selection
2. User sends 1–5 garments (batch or sequential) without choosing a mode
3. "See it on me" works with 1+ items for 1 try-on
4. Active photo always shown in cart status messages
5. Unfinished look restored within 24h on return
6. All new copy follows brand kit (try-ons, no AI)

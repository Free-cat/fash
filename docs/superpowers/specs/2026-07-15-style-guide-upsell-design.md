# Style Guide Upsell Design

**Date:** 2026-07-15  
**Status:** Approved  
**Locale:** English first (`bot/copy/en.py`), RU strings stubbed in `ru.py`  
**Depends on:** Try-on V1 (OpenRouter image generation, credit system)  
**Copy source:** FitRoom Brand Kit — Copy Rework (EN), Jul 2026

## Goal

After a successful try-on, offer a **Style Guide** upsell: a 1:1 editorial mood board showing how to wear the featured garment — pairing ideas, color palette, and accessories. Input is the **try-on result image**. Costs **1 try-on** (same credit unit as virtual try-on).

## Product Decisions (Approved)

| Decision | Choice |
|---|---|
| Pricing | 1 try-on per style guide |
| Trigger | Button on result screen **+** follow-up message after 30s if not tapped |
| Output | Image only (1:1 board) |
| Content scope | Focused: 3–4 outfit combos around THIS piece + color palette + 2–3 accessories |
| Generation | OpenRouter image model (same as try-on: `google/gemini-3.1-flash-image`) |
| Input image | Try-on result (`result_path` from `generations` table) |

## Copy Principles (from Brand Kit)

Apply to all Style Guide strings:

1. **Value-language, not currency** — say "try-on(s)", never "credit(s)"
2. **One clear next action** — message ends on single CTA; secondary options live in buttons
3. **Sell at the peak** — upsell lands on successful result (max emotion), not on errors
4. **Never say "AI"** — friend-stylist voice: warm, specific, human
5. **Errors keep the voice** — reassure try-on was refunded + one recovery step

## User Flow

```
Try-on completes
  → Send result photo with caption + action buttons
  → Primary button: [✨ What to pair with this] (callback: styleguide:{generation_id})
  → Schedule 30s delayed offer task

If user taps Style guide:
  → Validate generation belongs to user
  → If style_guide_path already set → resend saved board (no charge)
  → If balance < 1 → paywall / deficit flow (same as try-on, brand-kit copy)
  → Deduct 1 try-on
  → Show "Putting your style board together… about 20 sec ✨"
  → Call OpenRouter with result image + structured prompt
  → Save style_guide_{generation_id}.jpg
  → Send board photo with caption + action buttons
  → On failure: refund try-on, show friendly error

If user ignores for 30s:
  → Send offer message with same Style guide button
  → Skip if: style guide already exists, balance = 0, or user already tapped
```

## Copy — Flow 15: Style Guide Upsell

### Result screen — primary button (always on result keyboard)

| Key | Text |
|---|---|
| `btn_style_guide` | `✨ What to pair with this` |

**Why:** Value-led label — tells them what they get, not what the product is called. Icon for scannability (kit §13).

### 30s follow-up offer (if not tapped)

| Key | Text |
|---|---|
| `style_guide_offer` | `Love this look? 🔥 Get a style board for this piece — what to pair, colors & accessories. *1 try-on.*` |

**Why:** Sells at peak emotion (kit §07). Names the deliverable + price in value terms. One ask.

### Processing

| Key | Text |
|---|---|
| `style_guide_generating` | `Putting your style board together… about 20 sec ✨` |

**Why:** Matches kit §06 processing tone ("about 15 sec" not "~15").

### Style guide delivered — image caption

| Key | Text |
|---|---|
| `style_guide_caption` | `Your style board — pairings, colors & accessories for this look 👗` |

**Why:** Confirms value received; ends on the benefit, not a generic "here's your guide."

### Already generated — resend (no charge)

| Key | Text |
|---|---|
| `style_guide_already` | `You've already got a style board for this look 👇` |

**Why:** Reframes as "handled" not "blocked" (kit §04 photo limit pattern).

### Generation failed — API error

| Key | Text |
|---|---|
| `style_guide_failed` | `That one didn't come through — and I've refunded your try-on. Mind giving it another go?` |

**Why:** Matches kit §06/§07 error voice — refund as done favor + invite retry. `{error}` appended only in debug/admin, not shown to user in V1.

### Try-on not found / expired

| Key | Text |
|---|---|
| `style_guide_not_found` | `I can't find that try-on anymore. Send a clothing photo and let's style something new 👗` |

**Why:** Cause + fix in one line (kit §06 no-saved-photos pattern).

### Zero balance — reuse existing paywall strings

Style guide handler reuses brand-kit paywall copy (not new strings):

- Never paid → result paywall caption + shop keyboard
- Paid before → deficit caption + starter keyboard

## Integration with Flow 07 (Result captions)

Result caption stays focused on the wow moment. Style guide is a **separate button row**, not mixed into caption text — keeps one clear primary action per surface (kit principle §2).

Updated result keyboard layout (brand kit §07):

```
Row 1: [✨ What to pair with this]          ← Style guide (NEW, primary upsell)
Row 2: [👗 Try another] [💫 Invite friends]
Row 3: [📤 Share with friends]
Row 4: [⭐ Buy try-ons]  (if balance ≤ 2)
```

## Prompt Design

Structured JSON prompt (same pattern as `build_tryon_prompt()`):

- **Task:** `personal_style_guide_board`
- **Input:** `image_1` = try-on result (person wearing the featured garment)
- **Layout:** 1:1 square; top-left portrait (same person); right side 3–4 outfit combos anchored on the featured piece; bottom color palette (5–7 swatches) + 2–3 accessories
- **Style:** Minimal, modern, magazine editorial; soft warm beige background (`#F5F0EB`); clean grid with readable labels
- **Infer from image:** style season/type, undertone (warm/cool/neutral), complementary colors — do NOT hardcode gender or season names
- **Identity lock:** Same face, skin tone, hair; natural texture; no distortion
- **Negative:** Different person, cluttered layout, watermarks, cartoon, cropped face

OpenRouter config: `aspect_ratio: "1:1"`, `image_size: "1K"`.

## Architecture

### New / Modified Components

| Component | Responsibility |
|---|---|
| `bot/services/openrouter.py` | `build_style_guide_prompt()`, `generate_style_guide(result_image)` |
| `bot/handlers/styleguide.py` | Callback handler, delayed offer task, generation orchestration |
| `bot/handlers/tryon.py` | Pass `generation_id` to result keyboard; schedule 30s offer |
| `bot/keyboards.py` | `result_keyboard(balance, generation_id)` adds Style guide as row 1 |
| `bot/db/database.py` | Migration: `style_guide_path`, `style_guide_at` on `generations`; `record_generation` returns id |
| `bot/services/openrouter.py` `FileStorage` | `save_style_guide_photo()` |
| `bot/copy/en.py` + `Copy` dataclass | Brand-kit Style Guide strings (Flow 15) |
| `bot/main.py` | Register `styleguide.router` |

### Database Migration

```sql
ALTER TABLE generations ADD COLUMN style_guide_path TEXT;
ALTER TABLE generations ADD COLUMN style_guide_at TEXT;
```

### Credit & Guard Rules

- Reuse `GenerationGuard` for concurrent job limit
- Reuse circuit breaker on OpenRouter failures
- Refund 1 try-on on generation failure
- One style guide per generation; replays are free (resend saved image)

## Analytics Events

| Event | When |
|---|---|
| `style_guide_offered` | 30s follow-up sent |
| `style_guide_clicked` | User taps button |
| `style_guide_generated` | Board delivered |
| `style_guide_failed` | API error after deduct |

## Out of Scope (V1)

- Separate Stars pricing for style guides
- Text-only style advice without image
- Regenerate / refresh style guide for same look
- Full brand-kit copy rollout for all 13 existing flows (separate task — see plan Task 0)
- RU copy polish

## Success Criteria

1. After try-on, user sees `✨ What to pair with this` as first button
2. If ignored, brand-voice offer arrives ~30s later
3. Tapping deducts 1 try-on and returns 1:1 board image
4. Second tap resends without charging
5. Failures refund try-on with friendly copy; no "AI" or "credit" language anywhere

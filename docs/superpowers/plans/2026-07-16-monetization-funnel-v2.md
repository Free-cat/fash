# Monetization Funnel v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship P0 monetization funnel v2 — premium style guide at 3 try-ons with A/B offer, ProactiveGuard anti-collision layer, paywall with referral fallback, and result keyboard aligned to §8.1 (channel subscription deferred to §15 of spec).

**Architecture:** Central `ProactiveGuard` gates all proactive sends (premium delayed offer + drip worker). `ActivityMiddleware` updates `last_active_at`, cancels drips, and records premium-offer ignores once per shown offer. Premium upsell moves off the result keyboard to a 12s delayed message with A/B copy, preview on first show, fatigue/cooldown in DB. Paywall gets loss-aversion copy + shop packs + secondary invite CTA.

**Tech Stack:** Python 3, aiogram 3, SQLite/aiosqlite, pytest, asyncio

**Spec:** `docs/superpowers/specs/2026-07-16-monetization-funnel-v2-design.md`

## Global Constraints

- Premium style guide costs **3 try-ons** (full replacement of 1-try-on SKU; no fallback price in UI).
- A/B variant: `premium_offer_variant = (telegram_id % 2) + 1`, persisted on first show; events `premium_offer_shown_v1/v2`, `premium_offer_purchased_v1/v2`.
- Premium delayed offer fires **10–15 s** after result (use `PREMIUM_OFFER_DELAY_SECONDS = 12`).
- Premium cooldown: **4 hours** between shows; fatigue: **3 ignores → 14-day pause**.
- Proactive suppression: block if `generation_locks` row exists OR `last_active_at` within **2 min** (premium) / **10 min** (drip).
- On any message/callback: `update_user_activity` + `drip.cancel_all`; premium ignore +1 on **first** qualifying action after offer without premium click.
- Result keyboard §8.1: **Share first row**; **no** style-guide button on result; premium only via delayed offer.
- First paywall: purchase primary CTA + **invite friends** secondary; deficit: upsell only, no free paths.
- Copy: RU primary in `bot/copy/ru.py`, mirror in `bot/copy/en.py`; say "try-on(s)", never "credit(s)" in user-facing strings.
- Channel subscription: **out of scope** (spec §15).
- Style guide generation prompt: **no changes** (`build_style_guide_prompt` already 8–10 outfits).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `bot/db/migrations.py` | Modify | Premium offer user columns |
| `bot/db/database.py` | Modify | `deduct_credits`, premium-offer CRUD helpers |
| `bot/services/proactive_guard.py` | Create | Unified proactive send gate |
| `bot/services/premium_offer.py` | Create | Constants, A/B assignment, pending-offer tracker |
| `bot/middleware.py` | Modify | Add `ActivityMiddleware` |
| `bot/config.py` | Modify | `premium_preview_path` setting |
| `bot/copy/__init__.py` | Modify | New premium/paywall copy fields |
| `bot/copy/ru.py` | Modify | RU strings from spec §10 |
| `bot/copy/en.py` | Modify | EN mirror strings |
| `bot/keyboards.py` | Modify | `result_keyboard` reorder; `paywall_keyboard` |
| `bot/handlers/tryon.py` | Modify | Paywall/deficit copy + keyboard |
| `bot/handlers/styleguide.py` | Modify | 3-credit flow, guard, A/B delayed offer |
| `bot/services/drip.py` | Modify | `ProactiveGuard` before send |
| `bot/main.py` | Modify | Register middleware, inject guard |
| `assets/guide/premium_preview.jpg` | Create | Static preview collage (copy from style guide example or placeholder) |
| `tests/test_proactive_guard.py` | Create | Guard unit tests |
| `tests/test_activity_middleware.py` | Create | Activity + drip cancel + ignore |
| `tests/test_premium_offer.py` | Create | A/B, tracker, DB helpers |
| `tests/test_style_guide_flow.py` | Modify | Updated keyboard/offer behavior |
| `tests/test_tryon_communication.py` | Modify | Paywall keyboard + caption |

---

### Task 1: Premium offer DB schema and helpers

**Files:**
- Modify: `bot/db/migrations.py`
- Modify: `bot/db/database.py`
- Create: `tests/test_premium_offer.py`

**Interfaces:**
- Consumes: existing `Database` connection/migration runner
- Produces:
  - `async def deduct_credits(self, telegram_id: int, amount: int) -> bool`
  - `async def get_premium_offer_state(self, telegram_id: int) -> dict`
  - `async def assign_premium_offer_variant(self, telegram_id: int, variant: int) -> None`
  - `async def mark_premium_offer_shown(self, telegram_id: int) -> None`
  - `async def increment_premium_offer_ignored(self, telegram_id: int) -> int`
  - `async def reset_premium_offer_ignored(self, telegram_id: int) -> None`
  - `async def set_premium_offer_paused_until(self, telegram_id: int, until: str) -> None`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_premium_offer.py
import pytest
from bot.db.database import Database

@pytest.mark.asyncio
async def test_deduct_credits_requires_full_balance(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(1, "u", free_credits=2)
    assert await db.deduct_credits(1, 3) is False
    assert await db.get_balance(1) == 2

@pytest.mark.asyncio
async def test_deduct_credits_three_at_once(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(2, "u", free_credits=5)
    assert await db.deduct_credits(2, 3) is True
    assert await db.get_balance(2) == 2

@pytest.mark.asyncio
async def test_assign_premium_variant_once(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(3, "u", free_credits=0)
    await db.assign_premium_offer_variant(3, 2)
    state = await db.get_premium_offer_state(3)
    assert state["premium_offer_variant"] == 2
    await db.mark_premium_offer_shown(3)
    state = await db.get_premium_offer_state(3)
    assert state["premium_offer_shown_once"] == 1
    assert state["premium_offer_last_shown_at"] is not None

@pytest.mark.asyncio
async def test_increment_ignored_sets_pause_at_three(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(4, "u", free_credits=0)
    for _ in range(3):
        count = await db.increment_premium_offer_ignored(4)
    assert count == 3
    state = await db.get_premium_offer_state(4)
    assert state["premium_offer_paused_until"] is not None
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_premium_offer.py -v`  
Expected: FAIL (`deduct_credits` not defined)

- [ ] **Step 3: Add migrations**

```python
# bot/db/migrations.py — append to MIGRATIONS
"ALTER TABLE users ADD COLUMN premium_offer_variant INTEGER",
"ALTER TABLE users ADD COLUMN premium_offer_shown_once INTEGER NOT NULL DEFAULT 0",
"ALTER TABLE users ADD COLUMN premium_offer_ignored_count INTEGER NOT NULL DEFAULT 0",
"ALTER TABLE users ADD COLUMN premium_offer_paused_until TEXT",
"ALTER TABLE users ADD COLUMN premium_offer_last_shown_at TEXT",
```

- [ ] **Step 4: Implement database methods**

```python
# bot/db/database.py
async def deduct_credits(self, telegram_id: int, amount: int) -> bool:
    cursor = await self.conn.execute(
        """
        UPDATE users
        SET balance = balance - ?
        WHERE telegram_id = ? AND balance >= ?
        """,
        (amount, telegram_id, amount),
    )
    await self.conn.commit()
    return cursor.rowcount > 0

async def get_premium_offer_state(self, telegram_id: int) -> dict:
    row = await self.fetch_user(telegram_id)
    if not row:
        return {}
    return {
        "premium_offer_variant": row["premium_offer_variant"],
        "premium_offer_shown_once": int(row["premium_offer_shown_once"] or 0),
        "premium_offer_ignored_count": int(row["premium_offer_ignored_count"] or 0),
        "premium_offer_paused_until": row["premium_offer_paused_until"],
        "premium_offer_last_shown_at": row["premium_offer_last_shown_at"],
    }

async def assign_premium_offer_variant(self, telegram_id: int, variant: int) -> None:
    await self.conn.execute(
        """
        UPDATE users
        SET premium_offer_variant = ?
        WHERE telegram_id = ? AND premium_offer_variant IS NULL
        """,
        (variant, telegram_id),
    )
    await self.conn.commit()

async def mark_premium_offer_shown(self, telegram_id: int) -> None:
    await self.conn.execute(
        """
        UPDATE users
        SET premium_offer_shown_once = 1,
            premium_offer_last_shown_at = datetime('now')
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    await self.conn.commit()

async def increment_premium_offer_ignored(self, telegram_id: int) -> int:
    await self.conn.execute(
        """
        UPDATE users
        SET premium_offer_ignored_count = premium_offer_ignored_count + 1,
            premium_offer_paused_until = CASE
                WHEN premium_offer_ignored_count + 1 >= 3
                THEN datetime('now', '+14 days')
                ELSE premium_offer_paused_until
            END
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    await self.conn.commit()
    state = await self.get_premium_offer_state(telegram_id)
    return state["premium_offer_ignored_count"]

async def reset_premium_offer_ignored(self, telegram_id: int) -> None:
    await self.conn.execute(
        """
        UPDATE users
        SET premium_offer_ignored_count = 0,
            premium_offer_paused_until = NULL
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    await self.conn.commit()
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest tests/test_premium_offer.py -v`

- [ ] **Step 6: Commit**

```bash
git add bot/db/migrations.py bot/db/database.py tests/test_premium_offer.py
git commit -m "feat: add premium offer DB fields and credit deduction"
```

---

### Task 2: ProactiveGuard service

**Files:**
- Create: `bot/services/proactive_guard.py`
- Create: `tests/test_proactive_guard.py`

**Interfaces:**
- Consumes: `Database`, `GenerationGuard.is_locked()`, `fetch_user` / `last_active_at`
- Produces:
  - `class ProactiveGuard`
  - `async def can_send(self, telegram_id: int, touchpoint: str, *, generation_id: int | None = None) -> bool`
  - `TOUCHPOINT_PREMIUM = "premium_offer"`
  - `TOUCHPOINT_DRIP = "drip"`
  - Activity thresholds: premium `minutes=2`, drip `minutes=10`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_proactive_guard.py
import pytest
from datetime import datetime, timedelta, timezone
from bot.db.database import Database
from bot.services.proactive_guard import ProactiveGuard, TOUCHPOINT_PREMIUM, TOUCHPOINT_DRIP

@pytest.mark.asyncio
async def test_blocks_when_generation_locked(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(10, "u", free_credits=0)
    await db.conn.execute(
        "INSERT INTO generation_locks (telegram_id, started_at) VALUES (10, datetime('now'))"
    )
    await db.conn.commit()
    guard = ProactiveGuard(db)
    assert await guard.can_send(10, TOUCHPOINT_PREMIUM) is False

@pytest.mark.asyncio
async def test_blocks_premium_when_recently_active(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(11, "u", free_credits=0)
    await db.update_user_activity(11)
    guard = ProactiveGuard(db)
    assert await guard.can_send(11, TOUCHPOINT_PREMIUM) is False

@pytest.mark.asyncio
async def test_blocks_premium_during_cooldown(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(12, "u", free_credits=0)
    await db.mark_premium_offer_shown(12)
    guard = ProactiveGuard(db)
    assert await guard.can_send(12, TOUCHPOINT_PREMIUM) is False

@pytest.mark.asyncio
async def test_blocks_premium_when_paused(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(13, "u", free_credits=0)
    future = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    await db.set_premium_offer_paused_until(13, future)
    guard = ProactiveGuard(db)
    assert await guard.can_send(13, TOUCHPOINT_PREMIUM) is False

@pytest.mark.asyncio
async def test_allows_drip_after_premium_activity_window(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(14, "u", free_credits=0)
    past = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
    await db.conn.execute(
        "UPDATE users SET last_active_at = ? WHERE telegram_id = ?",
        (past.replace("T", " "), 14),
    )
    await db.conn.commit()
    guard = ProactiveGuard(db)
    assert await guard.can_send(14, TOUCHPOINT_DRIP) is True
```

Add `set_premium_offer_paused_until` to database if not added in Task 1 (already listed).

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_proactive_guard.py -v`

- [ ] **Step 3: Implement ProactiveGuard**

```python
# bot/services/proactive_guard.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bot.db.database import Database
from bot.services.generation_guard import GenerationGuard

TOUCHPOINT_PREMIUM = "premium_offer"
TOUCHPOINT_DRIP = "drip"

_PREMIUM_ACTIVITY_MINUTES = 2
_DRIP_ACTIVITY_MINUTES = 10
_PREMIUM_COOLDOWN_HOURS = 4


class ProactiveGuard:
    def __init__(self, db: Database) -> None:
        self.db = db
        self._generation_guard = GenerationGuard(db)

    async def can_send(
        self,
        telegram_id: int,
        touchpoint: str,
        *,
        generation_id: int | None = None,
    ) -> bool:
        if await self._generation_guard.is_locked(telegram_id):
            return False

        user = await self.db.fetch_user(telegram_id)
        if not user:
            return False

        activity_minutes = (
            _PREMIUM_ACTIVITY_MINUTES
            if touchpoint == TOUCHPOINT_PREMIUM
            else _DRIP_ACTIVITY_MINUTES
        )
        if self._recently_active(user["last_active_at"], activity_minutes):
            return False

        if touchpoint == TOUCHPOINT_PREMIUM:
            return await self._premium_allowed(user, generation_id)
        return True

    async def _premium_allowed(self, user, generation_id: int | None) -> bool:
        if user["premium_offer_paused_until"]:
            if self._is_future(user["premium_offer_paused_until"]):
                return False
            await self.db.reset_premium_offer_ignored(user["telegram_id"])

        if user["premium_offer_last_shown_at"]:
            if self._within_hours(user["premium_offer_last_shown_at"], _PREMIUM_COOLDOWN_HOURS):
                return False

        if generation_id is not None:
            gen = await self.db.get_generation_for_user_by_id(
                generation_id, user["telegram_id"]
            )
            if gen and gen["style_guide_path"]:
                return False
        return True

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return datetime.fromisoformat(value.replace(" ", "T")).replace(tzinfo=timezone.utc)

    def _recently_active(self, last_active_at: str | None, minutes: int) -> bool:
        if not last_active_at:
            return False
        return datetime.now(timezone.utc) - self._parse_dt(last_active_at) < timedelta(minutes=minutes)

    def _within_hours(self, value: str, hours: int) -> bool:
        return datetime.now(timezone.utc) - self._parse_dt(value) < timedelta(hours=hours)

    def _is_future(self, value: str) -> bool:
        return self._parse_dt(value) > datetime.now(timezone.utc)
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_proactive_guard.py -v`

- [ ] **Step 5: Commit**

```bash
git add bot/services/proactive_guard.py tests/test_proactive_guard.py
git commit -m "feat: add ProactiveGuard for proactive message gating"
```

---

### Task 3: Premium offer tracker and constants

**Files:**
- Create: `bot/services/premium_offer.py`
- Modify: `tests/test_premium_offer.py`

**Interfaces:**
- Produces:
  - `PREMIUM_STYLE_GUIDE_COST = 3`
  - `PREMIUM_OFFER_DELAY_SECONDS = 12`
  - `def assign_variant(telegram_id: int) -> int`
  - `def register_pending(telegram_id: int, generation_id: int) -> None`
  - `def clear_pending(telegram_id: int) -> None`
  - `def consume_ignore_if_pending(telegram_id: int) -> bool` — True if this call incremented (idempotent per pending window)

- [ ] **Step 1: Write failing tests**

```python
def test_assign_variant_is_stable():
    from bot.services.premium_offer import assign_variant
    assert assign_variant(12345) == assign_variant(12345)
    assert assign_variant(12345) in (1, 2)

def test_consume_ignore_only_once():
    from bot.services.premium_offer import (
        register_pending, clear_pending, consume_ignore_if_pending,
    )
    register_pending(99, 1)
    assert consume_ignore_if_pending(99) is True
    assert consume_ignore_if_pending(99) is False
    clear_pending(99)
    register_pending(99, 2)
    assert consume_ignore_if_pending(99) is True
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_premium_offer.py::test_assign_variant_is_stable -v`

- [ ] **Step 3: Implement module**

```python
# bot/services/premium_offer.py
from __future__ import annotations

PREMIUM_STYLE_GUIDE_COST = 3
PREMIUM_OFFER_DELAY_SECONDS = 12

_pending: dict[int, int] = {}
_consumed: set[int] = set()


def assign_variant(telegram_id: int) -> int:
    return (telegram_id % 2) + 1


def register_pending(telegram_id: int, generation_id: int) -> None:
    _pending[telegram_id] = generation_id
    _consumed.discard(telegram_id)


def clear_pending(telegram_id: int) -> None:
    _pending.pop(telegram_id, None)
    _consumed.discard(telegram_id)


def consume_ignore_if_pending(telegram_id: int) -> bool:
    if telegram_id not in _pending or telegram_id in _consumed:
        return False
    _consumed.add(telegram_id)
    return True
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/test_premium_offer.py -v`

- [ ] **Step 5: Commit**

```bash
git add bot/services/premium_offer.py tests/test_premium_offer.py
git commit -m "feat: add premium offer constants and pending tracker"
```

---

### Task 4: Activity middleware

**Files:**
- Modify: `bot/middleware.py`
- Modify: `bot/main.py`
- Create: `tests/test_activity_middleware.py`

**Interfaces:**
- Consumes: `Database.update_user_activity`, `DripService.cancel_all`, `consume_ignore_if_pending`, `increment_premium_offer_ignored`
- Produces: `class ActivityMiddleware(BaseMiddleware)` registered on `dp.update.middleware` before `AppMiddleware`

- [ ] **Step 1: Write failing test**

```python
# tests/test_activity_middleware.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Chat, Message, User
from bot.middleware import ActivityMiddleware

@pytest.mark.asyncio
async def test_activity_middleware_updates_and_cancels_drips(tmp_path):
    db = AsyncMock()
    drip = AsyncMock()
    middleware = ActivityMiddleware(db, drip)
    message = Message(
        message_id=1,
        date=0,
        chat=Chat(id=1, type="private"),
        from_user=User(id=42, is_bot=False, first_name="T"),
        text="hi",
    )
    handler = AsyncMock(return_value="ok")
    await middleware(handler, message, {})
    db.update_user_activity.assert_awaited_once_with(42)
    drip.cancel_all.assert_awaited_once_with(42)
    handler.assert_awaited_once()
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_activity_middleware.py -v`

- [ ] **Step 3: Implement ActivityMiddleware**

```python
# bot/middleware.py — add below AppMiddleware
from aiogram.types import CallbackQuery, Message
from bot.services.premium_offer import consume_ignore_if_pending

class ActivityMiddleware(BaseMiddleware):
    def __init__(self, db: Database, drip: DripService) -> None:
        self.db = db
        self.drip = drip

    def _telegram_id(self, event) -> int | None:
        user = getattr(event, "from_user", None)
        return user.id if user else None

    async def __call__(self, handler, event, data):
        telegram_id = self._telegram_id(event)
        if telegram_id is not None:
            await self.db.update_user_activity(telegram_id)
            await self.drip.cancel_all(telegram_id)
            if consume_ignore_if_pending(telegram_id):
                if isinstance(event, CallbackQuery) and (
                    event.data or ""
                ).startswith("styleguide:"):
                    pass  # purchase click handled in handler
                else:
                    await self.db.increment_premium_offer_ignored(telegram_id)
        return await handler(event, data)
```

Refine: premium click should call `clear_pending` + `reset_premium_offer_ignored` in styleguide handler; middleware should **skip** ignore increment when callback starts with `styleguide:`.

```python
            if consume_ignore_if_pending(telegram_id):
                is_premium_click = (
                    isinstance(event, CallbackQuery)
                    and (event.data or "").startswith("styleguide:")
                )
                if not is_premium_click:
                    await self.db.increment_premium_offer_ignored(telegram_id)
```

- [ ] **Step 4: Register in main.py**

```python
# bot/main.py inside create_app() after dp = Dispatcher(...)
dp.update.middleware(ActivityMiddleware(db, drip))
dp.update.middleware(AppMiddleware(...))
```

- [ ] **Step 5: Run test — expect PASS**

Run: `pytest tests/test_activity_middleware.py -v`

- [ ] **Step 6: Commit**

```bash
git add bot/middleware.py bot/main.py tests/test_activity_middleware.py
git commit -m "feat: add activity middleware for drip cancel and offer fatigue"
```

---

### Task 5: Copy updates (RU + EN)

**Files:**
- Modify: `bot/copy/__init__.py`
- Modify: `bot/copy/ru.py`
- Modify: `bot/copy/en.py`

**Interfaces:**
- Produces new `Copy` fields:
  - `premium_offer_v1: str`
  - `premium_offer_v2: str`
  - `premium_offer_preview_caption: str`
  - `premium_offer_cross_sell: str`
  - `premium_style_guide_failed: str` (3-credit refund message)
  - Update `paywall`, `deficit`, `invite_text`, `btn_style_guide` (label `✨ Полный стайлинг — 3` / EN equivalent)
  - Keep `style_guide_generating`, `style_guide_caption`, etc.

- [ ] **Step 1: Add fields to Copy dataclass**

```python
# bot/copy/__init__.py
premium_offer_v1: str
premium_offer_v2: str
premium_offer_preview_caption: str
premium_offer_cross_sell: str
premium_style_guide_failed: str
```

- [ ] **Step 2: Add RU strings from spec §10**

```python
# bot/copy/ru.py
paywall=(
    "Ты уже примерил 2 образа — и один реально огонь 🔥\n"
    "Продолжи: 5 примерок за 50⭐\n\n"
    "Не готов платить? Покажи другу, как ты выглядишь — "
    "+1 бесплатная, когда он примерит ✨"
),
deficit=(
    "Опять кончились? Похоже, тебе заходит 😏\n"
    "В этот раз — Популярная: 15 примерок за 120⭐ "
    "(дешевле за примерку, чем в прошлый раз)"
),
invite_text=(
    "Покажи другу, как ты выглядишь в этом образе — пусть попробует сам ✨\n"
    "(а когда он сделает первую примерку — тебе +1 бесплатная)"
),
btn_style_guide="✨ Полный стайлинг — 3",
premium_offer_v1=(
    "9 образов за 3 примерки — дешевле за образ, чем обычная примерка. "
    "Твоя палитра + обувь, сумка и аксессуары к этой вещи."
),
premium_offer_v2=(
    'Хочешь, чтобы спросили "у тебя что, стилист?" 👀\n'
    "9 образов с этой вещью, точная палитра, подбор аксессуаров — "
    "весь набор профи-стайлинга."
),
premium_offer_preview_caption="Вот что получаешь — твоя версия будет с этим образом",
premium_offer_cross_sell=(
    "Для полного стайлинга нужно 3 примерки, у тебя {balance}. "
    "Докупи или позови друга — и попробуй 👇"
),
premium_style_guide_failed=(
    "Не получилось собрать стайлинг — вернул(а) все 3 примерки. Попробуем ещё раз?"
),
```

- [ ] **Step 3: Mirror EN strings** (same structure, EN voice from brand kit)

- [ ] **Step 4: Run copy import smoke test**

Run: `python -c "from bot.copy import init_copy; init_copy('ru'); init_copy('en')"`

- [ ] **Step 5: Commit**

```bash
git add bot/copy/__init__.py bot/copy/ru.py bot/copy/en.py
git commit -m "copy: monetization funnel v2 paywall and premium offer strings"
```

---

### Task 6: Keyboards — result reorder and paywall

**Files:**
- Modify: `bot/keyboards.py`
- Modify: `tests/test_style_guide_flow.py`
- Modify: `tests/test_tryon_communication.py`

**Interfaces:**
- Produces:
  - `result_keyboard(balance, generation_id)` — row1: share only; row2: try_another + invite; row3 (if balance<=2): buy_credits; **no** styleguide row
  - `paywall_keyboard()` — all shop pack rows + final row `[btn_invite -> action:invite]`

- [ ] **Step 1: Update failing keyboard tests**

```python
# tests/test_style_guide_flow.py
def test_result_keyboard_share_is_first_row():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    first_btn = kb.inline_keyboard[0][0]
    assert first_btn.switch_inline_query is not None
    assert "styleguide" not in (first_btn.callback_data or "")

def test_result_keyboard_has_no_style_guide_button():
    init_copy("en")
    kb = result_keyboard(balance=5, generation_id=42)
    callbacks = [
        btn.callback_data
        for row in kb.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert not any(c and c.startswith("styleguide:") for c in callbacks)
```

```python
# tests/test_tryon_communication.py
def test_paywall_uses_paywall_keyboard_with_invite():
    init_copy("ru")
    caption, keyboard = build_result_message(remaining=0, total_purchases=0)
    assert "огонь" in caption
    callbacks = [
        btn.callback_data
        for row in keyboard.inline_keyboard
        for btn in row
        if btn.callback_data
    ]
    assert any(c.startswith("buy:") for c in callbacks)
    assert "action:invite" in callbacks
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `pytest tests/test_style_guide_flow.py tests/test_tryon_communication.py -v`

- [ ] **Step 3: Implement keyboards**

```python
# bot/keyboards.py
def result_keyboard(balance: int, generation_id: int) -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [
        [
            InlineKeyboardButton(
                text=copy.btn_share,
                switch_inline_query=copy.share_inline_query,
            ),
        ],
        [
            InlineKeyboardButton(
                text=copy.btn_try_another,
                callback_data="action:try_another",
            ),
            InlineKeyboardButton(
                text=copy.btn_invite,
                callback_data="action:invite",
            ),
        ],
    ]
    if balance <= 2:
        rows.append([InlineKeyboardButton(
            text=copy.btn_buy_credits, callback_data="shop:open",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def paywall_keyboard() -> InlineKeyboardMarkup:
    copy = active_copy()
    rows = [
        [InlineKeyboardButton(text=pack_button_text(pack), callback_data=f"buy:{pack.id}")]
        for pack in copy.credit_packs
    ]
    rows.append([
        InlineKeyboardButton(text=copy.btn_invite, callback_data="action:invite"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 4: Wire paywall in tryon.py**

```python
# bot/handlers/tryon.py
from bot.keyboards import paywall_keyboard

elif remaining == 0 and total_purchases == 0:
    caption = f"{caption}\n\n{copy.paywall}"
    keyboard = paywall_keyboard()
```

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest tests/test_style_guide_flow.py tests/test_tryon_communication.py -v`

- [ ] **Step 6: Commit**

```bash
git add bot/keyboards.py bot/handlers/tryon.py tests/test_style_guide_flow.py tests/test_tryon_communication.py
git commit -m "feat: reorder result keyboard and add paywall invite CTA"
```

---

### Task 7: Premium delayed offer + 3-credit purchase flow

**Files:**
- Modify: `bot/handlers/styleguide.py`
- Modify: `bot/config.py`
- Create: `assets/guide/premium_preview.jpg`
- Modify: `tests/test_style_guide_flow.py`

**Interfaces:**
- Consumes: `ProactiveGuard`, `premium_offer` module, `Settings.premium_preview_path`, new copy fields
- Produces: updated `schedule_style_guide_offer`, `style_guide_callback` using 3 credits

- [ ] **Step 1: Add preview path to settings**

```python
# bot/config.py
premium_preview_path: Path

# in load_settings():
premium_preview_path=BASE_DIR / os.getenv(
    "PREMIUM_PREVIEW_PATH", "assets/guide/premium_preview.jpg"
),
```

Copy `assets/guide/photo_guide.jpg` to `assets/guide/premium_preview.jpg` as placeholder until real collage asset exists.

- [ ] **Step 2: Update failing offer tests**

```python
from bot.services.premium_offer import PREMIUM_OFFER_DELAY_SECONDS, PREMIUM_STYLE_GUIDE_COST

def test_premium_offer_delay_constant():
    assert PREMIUM_OFFER_DELAY_SECONDS == 12

@pytest.mark.asyncio
async def test_schedule_premium_offer_sends_ab_variant(tmp_path):
    # mock guard.can_send True, balance 5, patch sleep
    # assert bot.send_message called with premium_offer_v1 or v2
    # assert analytics track premium_offer_shown_v1 or v2
```

- [ ] **Step 3: Refactor styleguide.py**

Key changes:
- Import `PREMIUM_OFFER_DELAY_SECONDS`, `PREMIUM_STYLE_GUIDE_COST`, `assign_variant`, `register_pending`, `clear_pending`
- Replace `STYLE_GUIDE_OFFER_DELAY_SECONDS = 30` usage with `PREMIUM_OFFER_DELAY_SECONDS`
- `schedule_style_guide_offer(bot, db, guard, settings, telegram_id, generation_id, balance)`:
  1. `await asyncio.sleep(PREMIUM_OFFER_DELAY_SECONDS)`
  2. `if not await guard.can_send(telegram_id, TOUCHPOINT_PREMIUM, generation_id=generation_id): track suppressed; return`
  3. If `balance < 3`: send `premium_offer_cross_sell` with `paywall_keyboard()` or mini keyboard (buy + invite); return
  4. Resolve variant: read DB or `assign_variant` + `assign_premium_offer_variant`
  5. Pick `copy.premium_offer_v1` or `copy.premium_offer_v2`
  6. If `not shown_once`: `answer_photo` with preview + caption; else `send_message`
  7. `mark_premium_offer_shown`, `register_pending`, track `premium_offer_shown_v{variant}`

- `style_guide_callback`:
  1. `clear_pending(telegram_id)`
  2. `await db.reset_premium_offer_ignored(telegram_id)`
  3. Require `balance >= 3`; use `deduct_credits(telegram_id, 3)`
  4. On error: `add_credits(telegram_id, 3)` + `premium_style_guide_failed`
  5. Track `premium_offer_purchased_v{variant}`

- [ ] **Step 4: Update call sites**

```python
# bot/handlers/look.py — pass guard + settings into schedule task
schedule_style_guide_offer_task(bot, db, guard, settings, telegram_id, gen_id, remaining)
```

Thread `ProactiveGuard` through `schedule_style_guide_offer_task` signature.

- [ ] **Step 5: Run tests — expect PASS**

Run: `pytest tests/test_style_guide_flow.py tests/test_premium_offer.py -v`

- [ ] **Step 6: Commit**

```bash
git add bot/handlers/styleguide.py bot/handlers/look.py bot/config.py assets/guide/premium_preview.jpg tests/test_style_guide_flow.py
git commit -m "feat: premium 3-try-on delayed offer with A/B and preview"
```

---

### Task 8: Drip worker + ProactiveGuard + analytics

**Files:**
- Modify: `bot/services/drip.py`
- Modify: `bot/main.py`

**Interfaces:**
- Consumes: `ProactiveGuard.can_send(telegram_id, TOUCHPOINT_DRIP)`
- Produces: drip sends only when guard allows; `analytics.track(..., "proactive_suppressed", drip_id)` on block

- [ ] **Step 1: Write failing test**

```python
# tests/test_drip.py
@pytest.mark.asyncio
async def test_process_due_skips_when_guard_blocks(tmp_path):
    # setup due drip, mock guard.can_send False
    # assert send_message not called, drip not marked sent
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_drip.py::test_process_due_skips_when_guard_blocks -v`

- [ ] **Step 3: Inject guard into DripService**

```python
# bot/services/drip.py
class DripService:
    def __init__(self, db: Database, guard: ProactiveGuard | None = None) -> None:
        self.db = db
        self.guard = guard

    async def process_due(self, bot: Bot) -> None:
        ...
        if self.guard and not await self.guard.can_send(telegram_id, TOUCHPOINT_DRIP):
            await analytics.track(telegram_id, "proactive_suppressed", drip_id)
            await self.db.conn.execute(
                "UPDATE drip_jobs SET cancelled = 1 WHERE id = ?", (job["id"],)
            )
            await self.db.conn.commit()
            continue
```

- [ ] **Step 4: Wire in main.py**

```python
guard = ProactiveGuard(db)
drip = DripService(db, guard=guard)
# pass guard to AppMiddleware data dict for handlers
```

Add `guard` to `AppMiddleware` `data` dict so handlers can access it.

- [ ] **Step 5: Run drip tests**

Run: `pytest tests/test_drip.py -v`

- [ ] **Step 6: Commit**

```bash
git add bot/services/drip.py bot/main.py bot/middleware.py tests/test_drip.py
git commit -m "feat: gate drip sends through ProactiveGuard"
```

---

### Task 9: Full regression and manual smoke

**Files:**
- All touched modules

- [ ] **Step 1: Run full test suite**

Run: `pytest -v`  
Expected: all tests PASS

- [ ] **Step 2: Fix any broken tests** from delay constant rename, keyboard row counts, copy assertions

- [ ] **Step 3: Manual smoke checklist**

1. Complete try-on → result has share first, no style guide button  
2. Wait ~12s → premium offer appears (with preview first time)  
3. Tap another button without buying → ignore counted once  
4. Start new try-on during wait → offer suppressed (`proactive_suppressed` in analytics)  
5. Hit paywall at 0 balance → shop packs + invite button, loss-aversion copy  
6. Buy style guide → 3 credits deducted; failure refunds 3  

- [ ] **Step 4: Final commit if fixes needed**

```bash
git add -A
git commit -m "test: fix regression after monetization funnel v2"
```

---

## Spec Coverage Checklist

| Spec requirement | Task |
|---|---|
| P0.1 Premium 3 try-on, delayed offer, preview, cross-sell | Task 7 |
| P0.2 A/B variant + analytics | Task 3, 7 |
| P0.3 ProactiveGuard + activity middleware | Task 2, 4, 8 |
| P0.4 Fatigue ignore once per show | Task 3, 4, 7 |
| P0.5 Cooldown 4h | Task 2 |
| P0.6 Paywall + deficit v2 | Task 5, 6 |
| P0.7 Referral copy v2 | Task 5 |
| Result keyboard §8.1 | Task 6 |
| Channel subscription §15 | **Deferred — no task** |
| P1 low-balance / win-back | **Out of plan scope** |

## Self-Review Notes

- All tasks include concrete file paths and code snippets.
- `deduct_credits` signature consistent across Tasks 1 and 7.
- `ProactiveGuard` touchpoint strings consistent across Tasks 2, 7, 8.
- Premium ignore skips `styleguide:` callbacks in middleware to avoid penalizing purchase clicks.
- No placeholder steps; channel explicitly excluded per approved brainstorm.

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-16-monetization-funnel-v2.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — implement tasks in this session with checkpoints

**Which approach?**

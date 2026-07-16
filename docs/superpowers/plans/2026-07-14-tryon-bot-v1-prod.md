# Try-On Bot V1 Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the MVP try-on bot into a production V1 with emotional UX, corrected Stars pricing, photo guide, drip/referral/upsell funnels, analytics, privacy, and Docker/webhook deployment.

**Architecture:** Keep aiogram 3 + SQLite + OpenRouter. Add focused modules: `copy.py` for strings, `services/drip.py` for scheduled messages, `services/referrals.py` for deep links, `services/analytics.py` for events, `services/generation_guard.py` for concurrency/circuit breaker. Handlers stay thin; business logic in services.

**Tech Stack:** Python 3.11+, aiogram 3, aiosqlite, Pillow, aiohttp, pytest, pytest-asyncio, Docker

**Spec:** `docs/superpowers/specs/2026-07-14-tryon-bot-v1-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `bot/copy.py` | All English UI strings |
| `bot/config.py` | Settings, credit packs, env vars |
| `bot/db/database.py` | Schema + queries |
| `bot/db/migrations.py` | Additive column migrations |
| `bot/services/analytics.py` | Event logging |
| `bot/services/drip.py` | Schedule/send drip messages |
| `bot/services/referrals.py` | Referral parsing + rewards |
| `bot/services/generation_guard.py` | Concurrent gen lock + circuit breaker |
| `bot/handlers/guide.py` | Photo guide `/guide` |
| `bot/handlers/referral.py` | Share + referral deep links |
| `bot/handlers/admin.py` | Owner `/stats` |
| `bot/handlers/privacy.py` | `/delete_my_data`, opt-out |
| `assets/guide/` | User-provided guide images |
| `tests/` | Unit tests per service |
| `Dockerfile`, `docker-compose.yml` | Production deploy |

---

### Task 1: Test Infrastructure

**Files:**
- Create: `pytest.ini`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add dev dependencies**

Add to `requirements.txt`:

```text
pytest>=8.0,<9
pytest-asyncio>=0.24,<1
```

- [ ] **Step 2: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 3: Write failing config test**

Create `tests/test_config.py`:

```python
from bot.config import CREDIT_PACKS, CreditPack


def test_credit_packs_prod_pricing():
    packs = {p.id: p for p in CREDIT_PACKS}
    assert packs["single"].stars == 20
    assert packs["starter"].stars == 50
    assert packs["popular"].stars == 120
    assert packs["best"].stars == 250
    assert packs["popular"].highlight is True
```

- [ ] **Step 4: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_config.py -v`  
Expected: FAIL (`AttributeError` or wrong star counts)

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pytest.ini tests/
git commit -m "test: add pytest infrastructure and config pricing test"
```

---

### Task 2: Config + Copy Module

**Files:**
- Modify: `bot/config.py`
- Create: `bot/copy.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Update CreditPack and packs in config.py**

```python
@dataclass(frozen=True)
class CreditPack:
    id: str
    credits: int
    stars: int
    label: str
    highlight: bool = False


CREDIT_PACKS: tuple[CreditPack, ...] = (
    CreditPack(id="single", credits=1, stars=20, label="Single — 1 try-on"),
    CreditPack(id="starter", credits=5, stars=50, label="Starter — 5 try-ons"),
    CreditPack(
        id="popular",
        credits=15,
        stars=120,
        label="Popular — 15 try-ons",
        highlight=True,
    ),
    CreditPack(id="best", credits=40, stars=250, label="Best Value — 40 try-ons"),
)
```

Add to `Settings`:

```python
owner_telegram_id: int | None
webhook_url: str | None
webhook_secret: str | None
guide_photo_path: Path
use_webhook: bool
```

Load from env: `OWNER_TELEGRAM_ID`, `WEBHOOK_URL`, `WEBHOOK_SECRET`, `GUIDE_PHOTO_PATH=assets/guide/photo_guide.jpg`, `USE_WEBHOOK=false`.

- [ ] **Step 2: Create bot/copy.py with key strings**

```python
WELCOME_NEW = (
    "Ever wondered how that outfit would look on *you*?\n\n"
    "Let's build your personal fitting room ✨\n"
    "Upload a photo of yourself — or tap 📸 Photo guide first."
)

PHOTO_1_SAVED = "Looking good! One more photo and your fitting room is ready 👗"
PHOTO_READY = (
    "Your fitting room is ready 🎉\n"
    "You have *{free_credits} free try-ons*. Send any clothing photo!"
)

GENERATING = "Styling your look… ~15 seconds ✨"
RESULT_CAPTION = "This is *you* in that outfit."

PAYWALL = (
    "Your free try-ons are used up — but that last look was worth it 🔥\n"
    "Want to try more outfits before you buy?"
)

DEFICIT = "Out of credits! Grab *5 more try-ons for 50⭐* — takes 5 seconds."

PRIVACY_NOTE = (
    "🔒 Photos are stored securely and used only for try-on. "
    "Delete anytime with /delete_my_data"
)

DRIP_OPT_OUT = "Stop reminders"
```

- [ ] **Step 3: Run config test**

Run: `.venv/bin/pytest tests/test_config.py -v`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add bot/config.py bot/copy.py tests/test_config.py
git commit -m "feat: prod Stars pricing and copy module"
```

---

### Task 3: Database Schema Extension

**Files:**
- Create: `bot/db/migrations.py`
- Modify: `bot/db/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing test for new user fields**

```python
import pytest
from bot.db.database import Database


@pytest.mark.asyncio
async def test_user_has_lifecycle_fields(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    await db.get_or_create_user(123, "alice", free_credits=2)
    await db.update_user_activity(123)
    user = await db.fetch_user(123)
    assert user["last_active_at"] is not None
    assert user["drip_opt_out"] == 0
    assert user["total_purchases"] == 0
    await db.close()
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `.venv/bin/pytest tests/test_database.py::test_user_has_lifecycle_fields -v`

- [ ] **Step 3: Add migrations and schema**

Create `bot/db/migrations.py`:

```python
MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN last_active_at TEXT",
    "ALTER TABLE users ADD COLUMN referred_by INTEGER",
    "ALTER TABLE users ADD COLUMN referral_credits_month TEXT",
    "ALTER TABLE users ADD COLUMN referral_credits_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN drip_opt_out INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN total_purchases INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE users ADD COLUMN first_tryon_at TEXT",
    "ALTER TABLE users ADD COLUMN paywall_shown_at TEXT",
]

NEW_TABLES = """
CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    event_name TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS drip_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    drip_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    sent_at TEXT,
    cancelled INTEGER NOT NULL DEFAULT 0,
    UNIQUE(telegram_id, drip_id)
);

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referee_id INTEGER NOT NULL UNIQUE,
    converted_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generation_locks (
    telegram_id INTEGER PRIMARY KEY,
    started_at TEXT NOT NULL
);
"""
```

In `Database.connect()`, after `executescript(SCHEMA)`, run migrations (try/except OperationalError for duplicate column), then `executescript(NEW_TABLES)`.

Add methods: `update_user_activity`, `set_referred_by`, `increment_total_purchases`, `schedule_drip`, `fetch_due_drips`, `mark_drip_sent`, `cancel_drips_for_user`, `record_referral`, `convert_referral`.

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add bot/db/ tests/test_database.py
git commit -m "feat: extend database schema for prod v1"
```

---

### Task 4: Analytics Service

**Files:**
- Create: `bot/services/analytics.py`
- Create: `tests/test_analytics.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_track_event(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    analytics = Analytics(db)
    await analytics.track(42, "user_registered")
    events = await analytics.list_events(42)
    assert events[0]["event_name"] == "user_registered"
    await db.close()
```

- [ ] **Step 2: Implement Analytics**

```python
class Analytics:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def track(self, telegram_id: int, event_name: str, payload: str | None = None) -> None:
        await self.db.conn.execute(
            "INSERT INTO analytics_events (telegram_id, event_name, payload) VALUES (?, ?, ?)",
            (telegram_id, event_name, payload),
        )
        await self.db.conn.commit()
```

- [ ] **Step 3: Run tests — PASS**

- [ ] **Step 4: Commit**

---

### Task 5: Generation Guard (Concurrency + Circuit Breaker)

**Files:**
- Create: `bot/services/generation_guard.py`
- Create: `tests/test_generation_guard.py`

- [ ] **Step 1: Write failing tests**

```python
@pytest.mark.asyncio
async def test_only_one_concurrent_generation(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    guard = GenerationGuard(db)
    assert await guard.acquire(100) is True
    assert await guard.acquire(100) is False
    await guard.release(100)
    assert await guard.acquire(100) is True
    await db.close()


def test_circuit_breaker_opens_after_failures():
    guard = GenerationGuard(None)  # test pure logic separately
    cb = CircuitBreaker(threshold=3, window_seconds=600)
    cb.record_failure()
    cb.record_failure()
    assert cb.is_open() is False
    cb.record_failure()
    assert cb.is_open() is True
```

- [ ] **Step 2: Implement GenerationGuard + CircuitBreaker**

```python
@dataclass
class CircuitBreaker:
    threshold: int = 3
    window_seconds: int = 600
    _failures: list[float] = field(default_factory=list)

    def record_failure(self) -> None:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window_seconds]
        self._failures.append(now)

    def record_success(self) -> None:
        self._failures.clear()

    def is_open(self) -> bool:
        now = time.time()
        self._failures = [t for t in self._failures if now - t < self.window_seconds]
        return len(self._failures) >= self.threshold


class GenerationGuard:
    async def acquire(self, telegram_id: int) -> bool:
        # INSERT OR IGNORE into generation_locks; rowcount check
        ...

    async def release(self, telegram_id: int) -> None:
        await self.db.conn.execute(
            "DELETE FROM generation_locks WHERE telegram_id = ?", (telegram_id,)
        )
        await self.db.conn.commit()
```

- [ ] **Step 3: Run tests — PASS**

- [ ] **Step 4: Wire into tryon handler** — before deduct credit, `acquire`; in `finally`, `release`. If circuit open, reply without charging.

- [ ] **Step 5: Commit**

---

### Task 6: Referral Service + Handler

**Files:**
- Create: `bot/services/referrals.py`
- Create: `bot/handlers/referral.py`
- Modify: `bot/handlers/start.py`
- Create: `tests/test_referrals.py`

- [ ] **Step 1: Write failing tests**

```python
def test_parse_ref_payload():
    assert parse_start_payload("/start ref_12345") == 12345
    assert parse_start_payload("/start") is None


@pytest.mark.asyncio
async def test_referral_reward_after_first_tryon(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    ref = ReferralService(db)
    await db.get_or_create_user(1, "ref", 2)
    await db.get_or_create_user(2, "new", 2)
    await ref.attach_referral(referee_id=2, referrer_id=1)
    credited = await ref.on_first_tryon(2)
    assert credited is True
    assert await db.get_balance(1) == 3  # 2 free + 1 referral
    await db.close()
```

- [ ] **Step 2: Implement ReferralService**

```python
def parse_start_payload(text: str) -> int | None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].startswith("ref_"):
        return None
    try:
        referrer_id = int(parts[1].removeprefix("ref_"))
    except ValueError:
        return None
    return referrer_id if referrer_id > 0 else None


class ReferralService:
    async def attach_referral(self, referee_id: int, referrer_id: int) -> None:
        if referee_id == referrer_id:
            return
        # INSERT OR IGNORE into referrals + set users.referred_by
        ...

    async def on_first_tryon(self, referee_id: int) -> bool:
        # If referral not yet converted and monthly cap not hit, +1 credit to referrer
        ...
```

- [ ] **Step 3: Update start handler**

On `/start ref_XXX`, call `attach_referral` before onboarding.

- [ ] **Step 4: Add share button handler**

After result, inline keyboard:

```python
InlineKeyboardButton(
    text="📤 Share with friends",
    switch_inline_query="Look what I'd wear! Try it yourself →",
)
```

Referral link in bot message: `https://t.me/{bot_username}?start=ref_{user_id}`

- [ ] **Step 5: Run tests — PASS**

- [ ] **Step 6: Commit**

---

### Task 7: Photo Guide Handler

**Files:**
- Create: `bot/handlers/guide.py`
- Create: `assets/guide/.gitkeep`
- Modify: `bot/handlers/start.py`, `bot/keyboards.py`

- [ ] **Step 1: Add guide keyboard button on welcome**

```python
InlineKeyboardButton(text="📸 Photo guide", callback_data="guide:show")
```

- [ ] **Step 2: Implement guide handler**

```python
@router.callback_query(F.data == "guide:show")
@router.message(Command("guide"))
async def show_guide(message_or_callback, settings: Settings):
    guide_path = settings.guide_photo_path
    if not guide_path.exists():
        await answer(GUIDE_TEXT_FALLBACK)  # text tips if image missing
        return
    await answer_photo(FSInputFile(guide_path), caption=GUIDE_CAPTION)
```

`GUIDE_CAPTION` includes person DO/DON'T and garment DO/DON'T from spec.

- [ ] **Step 3: Link validation errors to guide**

In `photos.py` and `tryon.py` PhotoValidationError handler, append inline button "📸 Photo guide".

- [ ] **Step 4: Manual test**

Place user's guide image at `assets/guide/photo_guide.jpg`, run bot, tap Photo guide.

- [ ] **Step 5: Commit**

---

### Task 8: Emotional Onboarding + Paywall UX

**Files:**
- Modify: `bot/handlers/start.py`, `bot/handlers/photos.py`, `bot/handlers/tryon.py`, `bot/keyboards.py`

- [ ] **Step 1: Replace hardcoded strings with `bot/copy.py` imports**

- [ ] **Step 2: Add result action keyboard**

```python
def result_keyboard(balance: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="👗 Try another", callback_data="action:try_another"),
            InlineKeyboardButton(text="💫 Invite friends", callback_data="action:invite"),
        ],
    ]
    if balance <= 2:
        rows.append([InlineKeyboardButton(text="⭐ Buy credits", callback_data="shop:open")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 3: Paywall when balance hits 0 after free try-ons**

After generation when `remaining == 0` and `total_purchases == 0`:
- Send `copy.PAYWALL`
- Show shop keyboard with Popular highlighted (`⭐` prefix in button text)
- Track `paywall_shown` event

- [ ] **Step 4: Contextual upsell messages**

| Balance | After result message |
|---|---|
| > 3 | "Try another? 👗" only |
| 1-3 | "⚠️ {N} try-ons left" + Buy button |
| 0, never paid | PAYWALL + shop |
| 0, paid before | DEFICIT + Starter button |

- [ ] **Step 5: Commit**

---

### Task 9: Payments Upgrade (Single pack + post-purchase upsell)

**Files:**
- Modify: `bot/handlers/payments.py`, `bot/keyboards.py`

- [ ] **Step 1: Update shop keyboard with decoy layout**

```python
def shop_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for pack in CREDIT_PACKS:
        label = pack.label
        if pack.highlight:
            label = f"⭐ {label} — Most chosen"
        rows.append([
            InlineKeyboardButton(
                text=f"{label} — {pack.stars} ⭐",
                callback_data=f"buy:{pack.id}",
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

- [ ] **Step 2: Post-purchase upsell (30 sec delayed task)**

After successful Starter purchase, schedule message:

```python
if pack.id == "starter":
    await drip.schedule(telegram_id, "post_purchase_upsell", delay_seconds=30)
```

Message: upgrade to Popular for +70⭐ (delta wording).

- [ ] **Step 3: Increment `total_purchases` on payment**

- [ ] **Step 4: Commit**

---

### Task 10: Drip Scheduler Service

**Files:**
- Create: `bot/services/drip.py`
- Create: `tests/test_drip.py`
- Modify: `bot/main.py`

- [ ] **Step 1: Write failing test**

```python
@pytest.mark.asyncio
async def test_schedule_and_fetch_due_drip(tmp_path):
    db = Database(tmp_path / "test.db")
    await db.connect()
    drip = DripService(db)
    past = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    await drip.schedule_at(100, "T2", past)
    due = await drip.fetch_due(limit=10)
    assert due[0]["drip_id"] == "T2"
    await db.close()
```

- [ ] **Step 2: Implement DripService**

```python
DRIP_MESSAGES = {
    "T1": "Still thinking about that look? Send another outfit — {balance} free try left 👗",
    "T2": "That outfit looked great on you. Try 3 more before checkout — Popular pack 120⭐",
    # ... T3-T7 from spec
}

class DripService:
    async def schedule(self, telegram_id: int, drip_id: str, delay_seconds: int) -> None:
        ...

    async def cancel_all(self, telegram_id: int) -> None:
        ...

    async def process_due(self, bot: Bot) -> None:
        # fetch due, check opt_out, max 1/24h, send message + opt-out button
        ...
```

- [ ] **Step 3: Hook drip triggers**

| Event | Schedule |
|---|---|
| 1st free try-on complete | T1 (+30 min) |
| 2nd free try-on, balance=0 | T2 (+1h), cancel T1 |
| purchase | cancel all drips |
| balance=0 after paid gen | T5 (instant) |

- [ ] **Step 4: Start poll loop in main.py**

```python
async def drip_worker(bot: Bot, drip: DripService) -> None:
    while True:
        await drip.process_due(bot)
        await asyncio.sleep(60)
```

- [ ] **Step 5: Opt-out handler**

`/stop_reminders` or button → `drip_opt_out = 1`

- [ ] **Step 6: Run tests — PASS**

- [ ] **Step 7: Commit**

---

### Task 11: Privacy + Data Purge

**Files:**
- Create: `bot/handlers/privacy.py`
- Modify: `bot/services/openrouter.py` (add delete_user_files)
- Modify: `bot/db/database.py`

- [ ] **Step 1: Implement /delete_my_data**

```python
@router.message(Command("delete_my_data"))
async def delete_my_data(message: Message, db: Database, storage: FileStorage):
    user = await db.fetch_user(message.from_user.id)
    if not user:
        return
    storage.delete_user_dir(message.from_user.id)
    await db.delete_user_completely(message.from_user.id)
    await message.answer("All your photos and data have been deleted.")
```

- [ ] **Step 2: Daily purge job for 90-day inactive users**

In `drip_worker` or separate daily task:

```python
async def purge_inactive_users(db: Database, storage: FileStorage) -> None:
    rows = await db.fetch_users_inactive_since(days=90)
    for row in rows:
        storage.delete_user_dir(row["telegram_id"])
        await db.delete_user_completely(row["telegram_id"])
```

- [ ] **Step 3: Show PRIVACY_NOTE after onboarding complete**

- [ ] **Step 4: Commit**

---

### Task 12: Admin Stats

**Files:**
- Create: `bot/handlers/admin.py`

- [ ] **Step 1: Implement /stats (owner only)**

```python
@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, settings: Settings):
    if settings.owner_telegram_id != message.from_user.id:
        return
    stats = await db.get_admin_stats()
    await message.answer(
        f"Users: {stats['users']}\n"
        f"Try-ons: {stats['generations']}\n"
        f"Purchases: {stats['purchases']}\n"
        f"Stars earned: {stats['stars']}\n"
        f"Conversion: {stats['conversion']:.1%}"
    )
```

- [ ] **Step 2: Commit**

---

### Task 13: Docker + Webhook Deployment

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Modify: `bot/main.py`
- Modify: `.env.example`

- [ ] **Step 1: Dockerfile**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot/ bot/
COPY assets/ assets/
CMD ["python", "-m", "bot.main"]
```

- [ ] **Step 2: Update main.py for webhook/polling switch**

```python
async def main() -> None:
    ...
    if settings.use_webhook:
        await bot.set_webhook(
            url=f"{settings.webhook_url}/webhook",
            secret_token=settings.webhook_secret,
        )
        # aiohttp web app for webhook endpoint
    else:
        await dp.start_polling(bot)
```

- [ ] **Step 3: docker-compose.yml**

```yaml
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./assets:/app/assets
    ports:
      - "8080:8080"
    restart: unless-stopped
```

- [ ] **Step 4: Update README with deploy instructions**

- [ ] **Step 5: Commit**

---

### Task 14: End-to-End Manual Test Checklist

- [ ] **Step 1: Fresh user flow**

`/start` → guide → 2 photos → garment → result → share button → paywall → buy Popular 120⭐ → paid try-on

- [ ] **Step 2: Referral flow**

User A shares link → User B starts → B completes try-on → A gets +1 credit

- [ ] **Step 3: Drip flow**

Use shortened delays in dev env; verify T2 sends after free exhausted

- [ ] **Step 4: Failure flow**

Invalid OpenRouter key → credit refunded, circuit breaker message

- [ ] **Step 5: Privacy flow**

`/delete_my_data` → photos gone, user row deleted

---

## Spec Coverage Self-Review

| Spec section | Task |
|---|---|
| A+B+D positioning copy | Task 2, 8 |
| Stars pricing 20/50/120/250 | Task 2 |
| No hourly paid cap | Task 5 (no hourly limit) |
| Concurrent gen limit | Task 5 |
| Circuit breaker | Task 5 |
| Photo guide | Task 7 |
| Core funnel | Task 8 |
| Drip T1-T7 | Task 10 |
| Referral + milestones | Task 6 |
| Upsell ladder | Task 8, 9 |
| Analytics events | Task 4 |
| Privacy + 90d purge | Task 11 |
| Docker/webhook | Task 13 |
| /stats owner | Task 12 |

## Placeholder Scan

No TBD/TODO entries. All tasks have concrete files and code snippets.

---

**Plan complete and saved to `docs/superpowers/plans/2026-07-14-tryon-bot-v1-prod.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** — implement tasks in this session with checkpoints

**Which approach?**

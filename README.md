# Try-On Bot (V1 Production)

Dual-brand Telegram bot for virtual clothing try-on with **Telegram Stars** payments.

| | EN | RU |
|---|---|---|
| **Brand** | FitRoom | Моя примерка |
| **@username** | @myfitroom_bot | @moya_primerka_bot |
| **Locale** | `BOT_LOCALE=en` | `BOT_LOCALE=ru` |

Same codebase, separate deployments (different `BOT_TOKEN` per bot).

Branding spec: `docs/superpowers/specs/2026-07-15-tryon-bot-branding.md`

## Features

- Upload one full-body photo once (stored and preprocessed)
- Send a clothing photo → AI try-on via OpenRouter (Gemini 2.5 Flash Image)
- 2 free credits on signup
- Buy credit packs with Telegram Stars
- Credit refund if generation fails
- Photo guide, drip reminders, referral rewards
- Privacy: `/delete_my_data` + automatic 90-day inactive purge
- Owner `/stats` dashboard

## Quick start (local dev)

### 1. Create a bot

Talk to [@BotFather](https://t.me/BotFather), create a bot, save the token.

For Stars payments, enable payments in BotFather if prompted (Stars work for digital goods without a payment provider token).

### 2. Get OpenRouter API key

Sign up at [openrouter.ai](https://openrouter.ai), create an API key.

### 3. Configure

```bash
cp .env.example .env
# Edit .env: BOT_TOKEN, OPENROUTER_API_KEY, BOT_LOCALE=en|ru
```

### 4. Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

Local dev uses **polling** by default (`USE_WEBHOOK=false` in `.env`).

## Production deploy

- **Coolify:** see [docs/deploy/coolify.md](docs/deploy/coolify.md)
- **Docker Compose:** webhook mode + port 8080 (below)

### Docker Compose (webhook)

```bash
cp .env.example .env
# Set BOT_TOKEN, OPENROUTER_API_KEY, USE_WEBHOOK=true, WEBHOOK_URL, WEBHOOK_SECRET
docker compose up -d --build
curl http://localhost:8080/health   # → ok
```

Persistent data is stored in the `bot-data` Docker volume (`/app/data` in the container).

### Manual Docker + reverse proxy

Set at minimum:

- `BOT_TOKEN` — Telegram bot token
- `OPENROUTER_API_KEY` — OpenRouter API key
- `BOT_LOCALE` — `en` for FitRoom or `ru` for Моя примерка
- `USE_WEBHOOK=true`
- `WEBHOOK_URL` — public HTTPS URL (e.g. `https://bot.example.com`)
- `WEBHOOK_SECRET` — random secret string (Telegram sends it in `X-Telegram-Bot-Api-Secret-Token`)
- `OWNER_TELEGRAM_ID` — your Telegram user ID for `/stats`

Optional asset paths: `GUIDE_PHOTO_PATH`, `DEMO_IMAGE_PATH`, `PREMIUM_PREVIEW_PATH` (defaults under `assets/`).

### Reverse proxy example

Point HTTPS to `http://localhost:8080/webhook` (nginx/Caddy/Traefik).  
`WEBHOOK_URL` = public base URL without `/webhook`.

Example nginx location:

```nginx
location /webhook {
    proxy_pass http://127.0.0.1:8080/webhook;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

`WEBHOOK_URL` must match the public URL Telegram will call (e.g. `https://bot.example.com` — the bot appends `/webhook` automatically).

Back up `/app/data` (or the `bot-data` volume) regularly.

## Credit packs (Stars)

| Pack | Credits | Stars |
|------|---------|-------|
| Single | 1 | 20 ⭐ |
| Starter | 5 | 50 ⭐ |
| Popular | 15 | 120 ⭐ |
| Best Value | 40 | 250 ⭐ |

## Bot commands

- `/start` — onboarding
- `/guide` — photo tips
- `/balance` — check credits
- `/shop` — buy credits
- `/photos` — re-upload person photos
- `/delete_my_data` — delete all your photos and account data
- `/stats` — owner-only usage stats
- `/help` — usage tips

## Project layout

```
bot/
  main.py              # entry point (polling or webhook)
  config.py            # settings & credit packs
  handlers/            # start, photos, tryon, payments, privacy, admin
  services/            # image processing, OpenRouter, storage, drip
  db/                  # SQLite
assets/guide/          # photo guide image
data/                  # local DB + images (gitignored)
Dockerfile
docker-compose.yml
```

## Privacy

- Users can delete all data anytime with `/delete_my_data`
- Users inactive for 90 days are purged automatically (daily job)
- Privacy note removed from onboarding; `/delete_my_data` still available

## v2 roadmap (Russian + rubles)

Same bot logic, swap:

- UI strings → Russian
- Payments → YooKassa via Telegram Payments API
- Currency → RUB

## Notes

- Person photos are resized to fit within 1024px and padded to 3:4 (never crop head/feet).
- Only one primary photo is sent per try-on (latest uploaded).
- Generation takes ~10–20 seconds depending on OpenRouter load.
- Try-on uses a structured JSON prompt that locks identity and requires head-to-toe framing.

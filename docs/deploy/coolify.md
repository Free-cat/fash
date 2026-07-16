# Deploy to Coolify

Telegram bot with **webhook** mode on port **8080**. One Coolify application per bot instance (FitRoom EN and Моя примерка RU are separate apps).

## Prerequisites

- Coolify server with Docker
- Git repo pushed (GitHub/GitLab/Gitea)
- Domain pointed to Coolify (e.g. `fitroom.example.com`)
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- OpenRouter API key from [openrouter.ai](https://openrouter.ai)
- Your Telegram user ID for `/stats` (`OWNER_TELEGRAM_ID`)

## 1. Create application

1. **+ New Resource** → **Application**
2. Connect the `Free-cat/fash` repository
3. **Build Pack: Dockerfile** (preferred — not Nixpacks)
4. **Base Directory:** `/` (repo root)
5. **Dockerfile Location:** `/Dockerfile`
6. **Port:** unused for polling; `8080` only if webhook
7. **Custom Start Command:** leave **empty** when using Dockerfile
8. **Health Check** (webhook only, optional):
   - Path: `/health`
   - Port: `/8080`
   - Method: GET
   - Expected: `200` with body `ok`

> Health check works only when `USE_WEBHOOK=true`. Polling has no HTTP server.

### Nixpacks crash: `/bin/bash: -c: option requires an argument`

Coolify is on **Nixpacks** with an empty start command. Fix one of:

**A — Switch to Dockerfile (recommended)**

1. Configuration → Build Pack → **Dockerfile**
2. Clear Custom Start Command
3. Redeploy

**B — Stay on Nixpacks**

1. Set **Custom Start Command** to exactly: `python -m bot.main`
2. Redeploy (repo also has `Procfile` + `nixpacks.toml`)

## 2. Domain & HTTPS

1. Open **Domains** for the application
2. Add domain, e.g. `fitroom.example.com`
3. Enable **HTTPS** (Coolify / Traefik handles Let's Encrypt)
4. Save — Coolify proxies `https://fitroom.example.com` → container `:8080`

Telegram will call: `https://fitroom.example.com/webhook`

## 3. Persistent storage

Mount a volume so SQLite and user photos survive redeploys:

| Container path | Purpose |
|----------------|---------|
| `/app/data` | `bot.db` + `storage/` (user photos, generations) |

In Coolify: **Persistent Storage** → add mount:

- **Destination:** `/app/data`
- **Name:** `bot-data` (or any label)

Without this, every redeploy wipes users and balance.

## 4. Environment variables

Set in Coolify **Environment Variables** (or **Secrets** for tokens):

### Required

| Variable | Example | Notes |
|----------|---------|-------|
| `BOT_TOKEN` | `123456:ABC...` | From BotFather |
| `OPENROUTER_API_KEY` | `sk-or-...` | OpenRouter key |
| `BOT_LOCALE` | `en` or `ru` | `en` = FitRoom, `ru` = Моя примерка |
| `USE_WEBHOOK` | `true` | Must be `true` in Coolify |
| `WEBHOOK_URL` | `https://fitroom.example.com` | Public URL **without** `/webhook` |
| `WEBHOOK_SECRET` | random 32+ chars | `openssl rand -hex 32` |

### Recommended

| Variable | Default | Notes |
|----------|---------|-------|
| `OWNER_TELEGRAM_ID` | — | Your Telegram ID for `/stats` |
| `OPENROUTER_MODEL` | `google/gemini-3.1-flash-image` | Try-on model |
| `OPENROUTER_STYLE_GUIDE_MODEL` | `google/gemini-3-pro-image` | Style guide model |
| `FREE_CREDITS` | `2` | Signup bonus |
| `DATABASE_PATH` | `data/bot.db` | Keep default with volume on `/app/data` |
| `STORAGE_PATH` | `data/storage` | Keep default |

### Optional assets (baked into image; override only if mounting custom files)

| Variable | Default |
|----------|---------|
| `GUIDE_PHOTO_PATH` | `assets/guide/photo_guide.jpg` |
| `DEMO_IMAGE_PATH` | `assets/demo/how_it_works.jpg` |
| `PREMIUM_PREVIEW_PATH` | `assets/guide/premium_preview.jpg` |

**Do not** set `DATABASE_PATH` or `STORAGE_PATH` outside `/app/data` unless you mount those paths too.

## 5. Deploy

1. **Deploy** (or enable auto-deploy on push)
2. Check logs for:
   ```
   Bot started (FitRoom / locale=en)
   Webhook server started on 0.0.0.0:8080 (https://fitroom.example.com/webhook)
   ```
3. Verify health: `curl https://fitroom.example.com/health` → `ok`
4. Message your bot — should respond immediately

## 6. Two bots (EN + RU)

Deploy **two separate Coolify applications** from the same repo:

| App | `BOT_TOKEN` | `BOT_LOCALE` | Domain |
|-----|-------------|--------------|--------|
| FitRoom | @myfitroom_bot token | `en` | `fitroom.example.com` |
| Моя примерка | @moya_primerka_bot token | `ru` | `primerka.example.com` |

Each app needs its own volume (`/app/data`) and `WEBHOOK_URL`.

## 7. Local smoke test (before Coolify)

```bash
cp .env.example .env
# Set USE_WEBHOOK=true, WEBHOOK_URL, WEBHOOK_SECRET, tokens

docker compose up -d --build
curl http://localhost:8080/health   # ok
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/bin/bash: -c: option requires an argument` (crash loop) | Build Pack is **Nixpacks** with empty start command, or blank Custom Start Command. **Fix:** switch Build Pack to **Dockerfile**, OR set Start Command to `python -m bot.main`, then Redeploy. |
| Bot silent after deploy | Check `USE_WEBHOOK=true`, `WEBHOOK_URL` matches domain (no trailing path) |
| 502 from domain | Container not listening — check port `8080`, app logs |
| Health check failing | Enable webhook mode; path `/health` on port `8080` |
| Data lost on redeploy | Add persistent volume on `/app/data` |
| `WEBHOOK_URL is required` | Set `WEBHOOK_URL` when `USE_WEBHOOK=true` |
| Webhook conflict | Only one instance per `BOT_TOKEN` (polling + webhook cannot run together) |

## Backup

Back up the volume contents regularly:

- `data/bot.db` — users, credits, analytics
- `data/storage/` — person photos and generation results

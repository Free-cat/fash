# Try-On Bot Branding Spec

**Date:** 2026-07-15  
**Status:** Approved  
**Avatar:** User-provided (not generated)

## Dual Brand Architecture

| | EN | RU |
|---|---|---|
| **Brand name** | FitRoom | Моя примерка |
| **@username** | @myfitroom_bot | @moya_primerka_bot |
| **Tagline** | See it on you | Увидь себя в этом |
| **Share text** | Look what I'd wear! Try it → | Смотри, как на мне! Примерь → |
| **Deployment** | `BOT_LOCALE=en` | `BOT_LOCALE=ru` |

Each bot is a separate deployment (own `BOT_TOKEN`, same codebase).

## Emotional Core

**Magic → Confidence** — the wow moment ("that's me!") leads to purchase confidence.

## Positioning (unchanged)

| Layer | Emotion | Role |
|---|---|---|
| A — Confident Shopper | "Will this look good on me?" | Paywall, deficit upsell |
| B — Style Explorer | "What if I tried this?" | Onboarding, retention |
| D — Social Share | "Look what I'd wear!" | Share + referral loop |

## Voice Rules

- Friendly stylist friend, not a robot
- Never say: AI, generated, neural network, Gemini
- Always say: see it on you, try-on, fitting room / примерочная
- Emoji: ✨ 🎉 👗 🔥 ⚠️ 🔒 📤 📸 — never 🤖

## Visual Identity

| Token | Value | Use |
|---|---|---|
| Primary | `#E8735A` | Buttons, accents, avatar background |
| Secondary | `#2D2D2D` | Text, contrast |
| Accent | `#F5F0EB` | Cards, guide background |
| Motif | Mirror / fitting-room frame | Avatar, marketing |

**Avoid:** purple AI gradients, neon, cold blue tech palette.

## BotFather Profile (set manually)

### EN — @myfitroom_bot

**Name:** FitRoom — Virtual Try-On

**About:**
```
See any outfit on you before you buy ✨

1. Upload your photo
2. Send clothing pic
3. See it on you in ~15 sec

2 free try-ons · Pay with ⭐ Stars
```

**Description:** Virtual fitting room in Telegram. Try clothes on your photo before you buy.

### RU — @moya_primerka_bot

**Name:** Моя примерка — виртуальная примерочная

**About:**
```
Примерь любой образ на себе — до покупки ✨

1. Загрузи своё фото
2. Отправь фото одежды
3. Увидь результат за ~15 сек

2 бесплатные примерки · Оплата ⭐ Stars
```

**Description:** Виртуальная примерочная в Telegram. Примерь одежду на своё фото до покупки.

## Differentiation vs Competitors

| Competitors (primerka_app, primerka_ai) | Us |
|---|---|
| "AI stylist", WB/article links | Emotion-first: "see it on **you**" |
| Functional only | Full funnel: free → wow → Stars → referral |
| RU-centric | Dual EN/RU product |

## Implementation

- `BOT_LOCALE=en|ru` selects all UI strings via `bot/copy/`
- Credit pack labels localized per locale
- Drip messages localized per locale
- Invoice titles use brand name

## Out of Scope

- Avatar generation (user-provided)
- Unified single-bot locale auto-detect (V2)
- Custom domain / mini-app branding

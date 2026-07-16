# Try-On Bot V1 Production Design

**Date:** 2026-07-14  
**Status:** Approved for implementation  
**Locale:** English  
**Payments:** Telegram Stars (XTR)

## Goal

Ship a production-ready Telegram virtual try-on bot that maximizes emotional conversion (A+B+D positioning), monetizes via Stars credit packs, and retains users through drip messages, contextual upsells, and referral loops.

## Positioning (A + B + D)

| Layer | Emotion | Role |
|---|---|---|
| A — Confident Shopper | "Will this look good on me?" | Paywall, deficit upsell |
| B — Style Explorer | "What if I tried this?" | Onboarding, post-result retention |
| D — Social Share | "Look what I'd wear!" | Share + referral viral loop |

**Voice:** Friendly, slightly playful, zero AI jargon. Say "see it on you", not "AI generation".

## Stars Pricing

Creator value: ~$0.013/Star. COGS per try-on: ~$0.034 (Gemini 2.5 Flash, optimized pipeline).

| Pack | Credits | Stars | Role |
|---|---|---|---|
| Free signup | 2 | 0 | Reciprocity hook |
| Single | 1 | 20 | Impulse fallback |
| Starter | 5 | 50 | Price anchor |
| Popular ⭐ | 15 | 120 | Decoy target (highlighted) |
| Best Value | 40 | 250 | Volume tier |

## Rate Limits & Abuse Control

- **Paid generations:** no hourly cap
- **Free credits:** max 2 per account (signup only)
- **Concurrent jobs:** max 1 active generation per user
- **Circuit breaker:** pause generations if OpenRouter error rate >30% in 10 min; never charge on failure
- **Referral rewards:** max 10 credits/month per referrer; reward only after referee completes first try-on

## Core Funnel

1. `/start` → emotional welcome (B)
2. Optional photo guide → upload 2 person photos
3. "Fitting room ready" → 2 free try-ons
4. Garment photo → WOW result + action buttons
5. Free exhausted → paywall (A) with 3 pack options
6. Paid loop → contextual upsell by balance

## Photo Guide

User-provided assets in `assets/guide/`. Bot sends guide on `/start` (button) and `/guide`. Validation errors link back to guide.

**Person DO:** full body, front-facing, arms visible, good light, plain background.  
**Garment DO:** item alone, plain background, no model.  
**Garment on model:** allowed but warned — "works best with clothing alone".

## Drip Triggers

| ID | Trigger | Delay | Purpose |
|---|---|---|---|
| T1 | 1st free used, idle | 30 min | B — try another |
| T2 | All free used, no purchase | 1 hour | A — paywall nudge |
| T3 | T2 ignored | 24 hours | B + FOMO |
| T4 | T3 ignored | 72 hours | A + social proof, Starter pack |
| T5 | Paid, balance = 0 | instant | A — deficit upsell |
| T6 | Paid, balance ≤ 2 | after result | B — low balance warning |
| T7 | Inactive 7 days | 7 days | Win-back, 10⭐ single discount |

Rules: max 1 drip/24h; stop drips 24h after purchase; "Stop reminders" opt-out in every drip.

## Referral

- Deep link: `t.me/Bot?start=ref_{telegram_id}`
- +1 credit when referee completes first try-on
- Milestones: 3 friends → +3 credits; 5 friends → +5 credits; 10 friends → +15 credits
- Block self-referral

## Privacy

- `/delete_my_data` — delete photos, generations, user row
- Auto-purge users inactive 90 days (photos + generations)
- Onboarding note: photos used only for try-on

## Analytics Events (SQLite)

`user_registered`, `photo_uploaded`, `onboarding_complete`, `guide_viewed`, `first_tryon`, `second_tryon`, `paywall_shown`, `purchase`, `share_clicked`, `referral_converted`, `drip_sent`, `drip_opt_out`

## Deployment

- Docker Compose
- Webhook mode for production (polling for local dev)
- Owner `/stats` command (OWNER_TELEGRAM_ID env var)

## Out of Scope (V2)

- Russian locale + YooKassa/RUB
- Telegram channel warming funnel
- Garment AI extraction from model photos
- Multi-tier quality (FLUX HD)
- Admin web dashboard

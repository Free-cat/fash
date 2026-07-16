# Premium Showcase Pricing — Design

**Date:** 2026-07-16  
**Status:** Approved (approach A)  
**Amends:** `2026-07-16-monetization-funnel-v2-design.md`

## Problem

After the first free try-on, balance is 1 but premium style guide costs 3. Users hit the paywall before experiencing the full styling product.

## Decision

**First full style guide per user costs 1 try-on (showcase). All subsequent full style guides cost 3 try-ons.**

## Behavior

| State | Cost | Copy |
|-------|------|------|
| `premium_showcase_used_at IS NULL` | 1 | Showcase A/B offer text + button "— 1" |
| `premium_showcase_used_at` set | 3 | Existing premium A/B offer text + button "— 3" |

- Set `premium_showcase_used_at` only after **successful** style guide generation.
- On generation error: refund the **actual deducted amount**; do **not** mark showcase used.
- Balance checks and cross-sell use dynamic `{cost}`.

## Data

```sql
ALTER TABLE users ADD COLUMN premium_showcase_used_at TEXT;
```

Helpers: `is_premium_showcase_available()`, `get_style_guide_cost()`, `mark_premium_showcase_used()`.

## Analytics

| Event | When |
|-------|------|
| `premium_showcase_offer_shown_v{1\|2}` | Delayed offer shown, showcase available |
| `premium_showcase_purchased_v{1\|2}` | User taps showcase offer |
| `premium_offer_shown_v{1\|2}` | Delayed offer shown, post-showcase |
| `premium_offer_purchased_v{1\|2}` | User taps post-showcase offer |

A/B variant assignment unchanged (per-user hash, sticky).

## Out of scope

- Changing regular (non-premium) 1-try-on style board upsell copy on result keyboard (removed in v2).
- Channel subscription gate.

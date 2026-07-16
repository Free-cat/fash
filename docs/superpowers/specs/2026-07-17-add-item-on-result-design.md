# Add Item On Result + Clear Look

**Date:** 2026-07-17  
**Status:** Approved

## Behavior

### Add item on result
1. After a successful try-on/look generation, bot stores `active_look_generation_id`.
2. Result keyboard includes `➕ Add item` and `🗑 Clear look`.
3. Tap Add item → enter waiting mode; ask for clothing photo; show Clear look.
4. User sends clothing photo → deduct 1 try-on → generate using **last result image + new garment**.
5. Send new result; update `active_look_generation_id`; exit waiting mode; schedule style guide offer.

### Clear look (hard reset)
Clears **all** look state for the user:
- look cart items
- `waiting_look_add_item`
- `active_look_generation_id`

Same button from cart UI and result / waiting UI.

## Data
```sql
ALTER TABLE users ADD COLUMN active_look_generation_id INTEGER;
ALTER TABLE users ADD COLUMN waiting_look_add_item INTEGER NOT NULL DEFAULT 0;
```

## Cost
Add-on generation = **1 try-on**.

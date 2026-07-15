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

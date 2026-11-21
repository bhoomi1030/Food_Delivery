"""Order lifecycle as an explicit state machine (no database access here)."""
from backend.exceptions import BusinessRuleError

PLACED = "PLACED"
CONFIRMED = "CONFIRMED"
PREPARING = "PREPARING"
OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
DELIVERED = "DELIVERED"
CANCELLED = "CANCELLED"

# status -> statuses it may move to
TRANSITIONS = {
    PLACED: {CONFIRMED, CANCELLED},
    CONFIRMED: {PREPARING, CANCELLED},
    PREPARING: {OUT_FOR_DELIVERY},
    OUT_FOR_DELIVERY: {DELIVERED},
    DELIVERED: set(),
    CANCELLED: set(),
}

# The happy path used when advancing an order step by step.
HAPPY_PATH = [PLACED, CONFIRMED, PREPARING, OUT_FOR_DELIVERY, DELIVERED]

ALL_STATUSES = frozenset(TRANSITIONS)


def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())


def ensure_transition(current: str, target: str) -> None:
    if current not in TRANSITIONS:
        raise BusinessRuleError(f"Unknown order status: {current}")
    if not can_transition(current, target):
        raise BusinessRuleError(f"Cannot move an order from {current} to {target}")


def next_status(current: str):
    """Next status on the happy path, or None if the order is finished."""
    if current not in HAPPY_PATH:
        return None
    index = HAPPY_PATH.index(current)
    return HAPPY_PATH[index + 1] if index + 1 < len(HAPPY_PATH) else None


def is_cancellable(current: str) -> bool:
    return can_transition(current, CANCELLED)

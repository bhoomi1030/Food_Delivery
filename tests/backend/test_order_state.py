"""Unit tests for the order lifecycle state machine."""
import pytest

from backend.exceptions import BusinessRuleError
from backend.services import order_state as s


def test_happy_path_walks_every_status_in_order():
    seen, current = [s.PLACED], s.PLACED
    while (nxt := s.next_status(current)) is not None:
        s.ensure_transition(current, nxt)
        seen.append(nxt)
        current = nxt
    assert seen == [s.PLACED, s.CONFIRMED, s.PREPARING, s.OUT_FOR_DELIVERY, s.DELIVERED]


@pytest.mark.parametrize("status", [s.PLACED, s.CONFIRMED])
def test_early_orders_can_be_cancelled(status):
    assert s.is_cancellable(status)
    s.ensure_transition(status, s.CANCELLED)


@pytest.mark.parametrize("status", [s.PREPARING, s.OUT_FOR_DELIVERY, s.DELIVERED, s.CANCELLED])
def test_late_or_finished_orders_cannot_be_cancelled(status):
    assert not s.is_cancellable(status)
    with pytest.raises(BusinessRuleError):
        s.ensure_transition(status, s.CANCELLED)


@pytest.mark.parametrize("status", [s.DELIVERED, s.CANCELLED])
def test_terminal_states_have_no_next_status_or_transitions(status):
    assert s.TRANSITIONS[status] == set()
    if status == s.CANCELLED:
        assert s.next_status(status) is None


def test_cannot_skip_a_step():
    with pytest.raises(BusinessRuleError, match="Cannot move"):
        s.ensure_transition(s.PLACED, s.DELIVERED)


def test_cannot_go_backwards():
    assert not s.can_transition(s.PREPARING, s.CONFIRMED)


def test_unknown_status_is_rejected():
    with pytest.raises(BusinessRuleError, match="Unknown"):
        s.ensure_transition("MYSTERY", s.CONFIRMED)

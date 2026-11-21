"""Unit tests for the pure pricing module (no database, no HTTP)."""
import pytest

from backend.exceptions import BusinessRuleError
from backend.services.pricing import CouponRule, calculate_bill, calculate_discount

WELCOME50 = CouponRule("WELCOME50", "PERCENT", 50, min_order=199, max_discount=100)
FLAT75 = CouponRule("FLAT75", "FLAT", 75, min_order=399)
EXPIRED = CouponRule("OLD", "PERCENT", 20, active=False)


def test_bill_without_coupon_adds_delivery_fee_and_tax():
    bill = calculate_bill(100)
    assert (bill.discount, bill.delivery_fee, bill.tax, bill.total) == (0, 40, 5, 145)


def test_delivery_is_free_at_threshold():
    bill = calculate_bill(499)
    assert bill.delivery_fee == 0
    assert bill.tax == 25  # 24.95 rounds half-up
    assert bill.total == 524


def test_delivery_fee_applies_just_below_threshold():
    assert calculate_bill(498).delivery_fee == 40


def test_empty_cart_costs_nothing():
    assert calculate_bill(0).total == 0


def test_negative_subtotal_is_rejected():
    with pytest.raises(BusinessRuleError):
        calculate_bill(-1)


def test_percent_coupon_is_capped_by_max_discount():
    assert calculate_discount(1000, WELCOME50) == 100


def test_percent_coupon_below_cap():
    assert calculate_discount(200, WELCOME50) == 100
    assert calculate_discount(199, WELCOME50) == 100  # 99.5 rounds half-up, then capped


def test_flat_coupon_applies_at_minimum():
    assert calculate_discount(399, FLAT75) == 75


def test_coupon_below_minimum_order_is_rejected():
    with pytest.raises(BusinessRuleError, match="minimum order"):
        calculate_discount(150, WELCOME50)


def test_inactive_coupon_is_rejected():
    with pytest.raises(BusinessRuleError, match="not active"):
        calculate_discount(500, EXPIRED)


def test_discount_never_exceeds_subtotal():
    big_flat = CouponRule("BIG", "FLAT", 500)
    assert calculate_discount(120, big_flat) == 120
    assert calculate_bill(120, big_flat).total == 40  # only the delivery fee remains


def test_unknown_coupon_type_is_rejected():
    with pytest.raises(BusinessRuleError, match="unknown type"):
        calculate_discount(100, CouponRule("X", "BOGUS", 5))


def test_full_bill_with_flat_coupon():
    bill = calculate_bill(400, FLAT75)
    assert (bill.subtotal, bill.discount, bill.delivery_fee, bill.tax, bill.total) == (400, 75, 40, 16, 381)


def test_bill_components_always_add_up():
    for subtotal in range(0, 1500, 37):
        bill = calculate_bill(subtotal)
        assert bill.total == bill.subtotal - bill.discount + bill.delivery_fee + bill.tax

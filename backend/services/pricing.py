"""Pure pricing logic: coupons, delivery fee, tax and totals (integer rupees)."""
from dataclasses import dataclass
from typing import Optional

from backend.config import DELIVERY_FEE, FREE_DELIVERY_ABOVE, TAX_PERCENT
from backend.exceptions import BusinessRuleError

PERCENT = "PERCENT"
FLAT = "FLAT"


@dataclass(frozen=True)
class CouponRule:
    code: str
    discount_type: str
    value: int
    min_order: int = 0
    max_discount: Optional[int] = None
    active: bool = True


@dataclass(frozen=True)
class Bill:
    subtotal: int
    discount: int
    delivery_fee: int
    tax: int
    total: int


def _percent_of(amount: int, percent: int) -> int:
    """Round-half-up percentage using integers only (avoids float drift)."""
    return (amount * percent + 50) // 100


def calculate_discount(subtotal: int, coupon: Optional[CouponRule]) -> int:
    if coupon is None:
        return 0
    if not coupon.active:
        raise BusinessRuleError(f"Coupon {coupon.code} is not active")
    if subtotal < coupon.min_order:
        raise BusinessRuleError(
            f"Coupon {coupon.code} needs a minimum order of ₹{coupon.min_order}"
        )
    if coupon.discount_type == PERCENT:
        discount = _percent_of(subtotal, coupon.value)
    elif coupon.discount_type == FLAT:
        discount = coupon.value
    else:
        raise BusinessRuleError(f"Coupon {coupon.code} has an unknown type")
    if coupon.max_discount is not None:
        discount = min(discount, coupon.max_discount)
    return min(discount, subtotal)


def calculate_bill(subtotal: int, coupon: Optional[CouponRule] = None) -> Bill:
    if subtotal < 0:
        raise BusinessRuleError("Subtotal cannot be negative")
    discount = calculate_discount(subtotal, coupon)
    delivery_fee = 0 if subtotal >= FREE_DELIVERY_ABOVE or subtotal == 0 else DELIVERY_FEE
    taxable = subtotal - discount
    tax = _percent_of(taxable, TAX_PERCENT)
    total = taxable + delivery_fee + tax
    return Bill(subtotal=subtotal, discount=discount, delivery_fee=delivery_fee, tax=tax, total=total)

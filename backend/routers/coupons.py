"""Coupon endpoints."""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.exceptions import BusinessRuleError
from backend.models import Coupon
from backend.schemas import BillOut, CouponOut, CouponValidateRequest
from backend.services.orders import find_coupon, to_rule
from backend.services.pricing import calculate_bill

router = APIRouter(prefix="/api/coupons", tags=["coupons"])


@router.get("", response_model=List[CouponOut])
def list_coupons(db: Session = Depends(get_db)):
    return db.scalars(select(Coupon).where(Coupon.active.is_(True)).order_by(Coupon.code)).all()


@router.post("/validate", response_model=BillOut)
def validate_coupon(payload: CouponValidateRequest, db: Session = Depends(get_db)):
    coupon = find_coupon(db, payload.code)
    if coupon is None:
        raise BusinessRuleError("Enter a coupon code")
    bill = calculate_bill(payload.subtotal, to_rule(coupon))
    return BillOut(**bill.__dict__, coupon_code=coupon.code)

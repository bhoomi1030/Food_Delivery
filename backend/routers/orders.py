"""Order endpoints (authenticated)."""
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Order, User
from backend.schemas import BillOut, OrderItemOut, OrderOut, OrderPage, PlaceOrderRequest, QuoteRequest
from backend.security import get_current_user
from backend.services import order_state, orders as order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


def order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=order.id, restaurant_id=order.restaurant_id, restaurant_name=order.restaurant.name,
        status=order.status, delivery_address=order.delivery_address, coupon_code=order.coupon_code,
        subtotal=order.subtotal, discount=order.discount, delivery_fee=order.delivery_fee,
        tax=order.tax, total=order.total, created_at=order.created_at,
        items=[OrderItemOut.model_validate(i) for i in order.items],
        can_cancel=order_state.is_cancellable(order.status),
        next_status=order_state.next_status(order.status),
    )


@router.post("/quote", response_model=BillOut)
def quote_order(payload: QuoteRequest, db: Session = Depends(get_db)):
    """Price a cart without creating anything (used by the cart UI)."""
    _restaurant, _lines, bill, coupon = order_service.price_cart(db, payload)
    return BillOut(**bill.__dict__, coupon_code=coupon.code if coupon else None)


@router.post("", response_model=OrderOut, status_code=201)
def place_order(
    payload: PlaceOrderRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(None, max_length=64),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    order, created = order_service.place_order(db, user, payload, idempotency_key)
    if not created:
        response.status_code = 200  # replay of an earlier request
    return order_out(order)


@router.get("", response_model=OrderPage)
def my_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, total = order_service.list_orders(db, user, page, page_size)
    return OrderPage(items=[order_out(o) for o in rows], total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return order_out(order_service.get_order_for_user(db, order_id, user))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = order_service.get_order_for_user(db, order_id, user)
    return order_out(order_service.cancel_order(db, order))


@router.post("/{order_id}/advance", response_model=OrderOut)
def advance_order(order_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Demo helper: moves the order along the happy path (stands in for the kitchen/rider apps)."""
    order = order_service.get_order_for_user(db, order_id, user)
    return order_out(order_service.advance_order(db, order))

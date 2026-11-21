"""Order use-cases: quoting, placing (idempotent), cancelling and advancing."""
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.exceptions import BusinessRuleError, ConflictError, ForbiddenError, NotFoundError
from backend.models import Coupon, MenuItem, Order, OrderItem, Restaurant, User
from backend.schemas import OrderLineIn, PlaceOrderRequest, QuoteRequest
from backend.services import order_state
from backend.services.pricing import Bill, CouponRule, calculate_bill


def to_rule(coupon: Coupon) -> CouponRule:
    return CouponRule(
        code=coupon.code, discount_type=coupon.discount_type, value=coupon.value,
        min_order=coupon.min_order, max_discount=coupon.max_discount, active=coupon.active,
    )


def find_coupon(db: Session, code: Optional[str]) -> Optional[Coupon]:
    if not code or not code.strip():
        return None
    coupon = db.scalar(select(Coupon).where(Coupon.code == code.strip().upper()))
    if coupon is None:
        raise NotFoundError(f"Coupon {code.strip().upper()} does not exist")
    return coupon


def _merge_lines(lines: List[OrderLineIn]) -> Dict[int, int]:
    """Combine duplicate menu items so the same dish is priced once."""
    merged: Dict[int, int] = {}
    for line in lines:
        merged[line.menu_item_id] = merged.get(line.menu_item_id, 0) + line.quantity
    return merged


def price_cart(db: Session, request: QuoteRequest):
    """Validate a cart against the live menu and return (restaurant, lines, bill, coupon)."""
    restaurant = db.get(Restaurant, request.restaurant_id)
    if restaurant is None:
        raise NotFoundError("Restaurant not found")
    if not restaurant.is_open:
        raise BusinessRuleError(f"{restaurant.name} is closed right now")

    merged = _merge_lines(request.items)
    menu_items = db.scalars(select(MenuItem).where(MenuItem.id.in_(merged.keys()))).all()
    by_id = {item.id: item for item in menu_items}

    lines = []
    for menu_item_id, quantity in merged.items():
        item = by_id.get(menu_item_id)
        if item is None or item.restaurant_id != restaurant.id:
            raise BusinessRuleError(f"Item {menu_item_id} does not belong to {restaurant.name}")
        if not item.is_available:
            raise BusinessRuleError(f"{item.name} is currently unavailable")
        if quantity > 10:
            raise BusinessRuleError(f"You can order at most 10 of {item.name}")
        lines.append((item, quantity))

    subtotal = sum(item.price * quantity for item, quantity in lines)
    coupon = find_coupon(db, request.coupon_code)
    bill = calculate_bill(subtotal, to_rule(coupon) if coupon else None)
    return restaurant, lines, bill, coupon


def quote(db: Session, request: QuoteRequest) -> Bill:
    return price_cart(db, request)[2]


def place_order(db: Session, user: User, request: PlaceOrderRequest, idempotency_key: Optional[str]) -> tuple:
    """Create an order. Returns (order, created). Replays return the original order."""
    if idempotency_key:
        existing = db.scalar(
            select(Order).where(Order.user_id == user.id, Order.idempotency_key == idempotency_key)
            .options(selectinload(Order.items), selectinload(Order.restaurant))
        )
        if existing is not None:
            return existing, False

    restaurant, lines, bill, coupon = price_cart(db, request)
    order = Order(
        user_id=user.id, restaurant_id=restaurant.id, status=order_state.PLACED,
        delivery_address=request.delivery_address,
        coupon_code=coupon.code if coupon else None,
        subtotal=bill.subtotal, discount=bill.discount, delivery_fee=bill.delivery_fee,
        tax=bill.tax, total=bill.total, idempotency_key=idempotency_key or None,
    )
    order.items = [
        OrderItem(menu_item_id=item.id, name=item.name, unit_price=item.price, quantity=quantity)
        for item, quantity in lines
    ]
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Duplicate order request")
    db.refresh(order)
    return order, True


def get_order_for_user(db: Session, order_id: int, user: User) -> Order:
    order = db.scalar(
        select(Order).where(Order.id == order_id)
        .options(selectinload(Order.items), selectinload(Order.restaurant))
    )
    if order is None:
        raise NotFoundError("Order not found")
    if order.user_id != user.id:
        raise ForbiddenError("You can only access your own orders")
    return order


def list_orders(db: Session, user: User, page: int, page_size: int):
    base = select(Order).where(Order.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    orders = db.scalars(
        base.order_by(Order.created_at.desc(), Order.id.desc())
        .options(selectinload(Order.items), selectinload(Order.restaurant))
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return orders, total


def _move(db: Session, order: Order, target: str) -> Order:
    order_state.ensure_transition(order.status, target)
    order.status = target
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: Order) -> Order:
    return _move(db, order, order_state.CANCELLED)


def advance_order(db: Session, order: Order) -> Order:
    target = order_state.next_status(order.status)
    if target is None:
        raise BusinessRuleError(f"Order is already {order.status} and cannot move further")
    return _move(db, order, target)

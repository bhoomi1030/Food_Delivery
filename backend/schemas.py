"""Pydantic request/response schemas (the public API contract)."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.config import MAX_DISTINCT_ITEMS, MAX_QTY_PER_ITEM


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth ----------
class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        local, _, domain = value.partition("@")
        if not local or "." not in domain or " " in value:
            raise ValueError("must be a valid email address")
        return value

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("must be at least 2 characters")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(ORMModel):
    id: int
    name: str
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- catalogue ----------
class MenuItemOut(ORMModel):
    id: int
    name: str
    description: str
    category: str
    price: int
    is_veg: bool
    is_available: bool


class RestaurantSummary(ORMModel):
    id: int
    name: str
    cuisine: str
    description: str
    emoji: str
    rating: float
    delivery_minutes: int
    is_veg: bool
    is_open: bool


class RestaurantDetail(RestaurantSummary):
    menu: List[MenuItemOut]


class RestaurantPage(BaseModel):
    items: List[RestaurantSummary]
    total: int
    page: int
    page_size: int
    cuisines: List[str]


# ---------- coupons ----------
class CouponOut(ORMModel):
    code: str
    description: str
    discount_type: str
    value: int
    min_order: int
    max_discount: Optional[int]


class CouponValidateRequest(BaseModel):
    code: str
    subtotal: int = Field(ge=0)


# ---------- orders ----------
class OrderLineIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=MAX_QTY_PER_ITEM)


class QuoteRequest(BaseModel):
    restaurant_id: int
    items: List[OrderLineIn] = Field(min_length=1, max_length=MAX_DISTINCT_ITEMS)
    coupon_code: Optional[str] = None


class PlaceOrderRequest(QuoteRequest):
    delivery_address: str = Field(min_length=8, max_length=300)

    @field_validator("delivery_address")
    @classmethod
    def _strip_address(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 8:
            raise ValueError("must be at least 8 characters")
        return value


class BillOut(BaseModel):
    subtotal: int
    discount: int
    delivery_fee: int
    tax: int
    total: int
    coupon_code: Optional[str] = None


class OrderItemOut(ORMModel):
    menu_item_id: int
    name: str
    unit_price: int
    quantity: int


class OrderOut(ORMModel):
    id: int
    restaurant_id: int
    restaurant_name: str
    status: str
    delivery_address: str
    coupon_code: Optional[str]
    subtotal: int
    discount: int
    delivery_fee: int
    tax: int
    total: int
    created_at: datetime
    items: List[OrderItemOut]
    can_cancel: bool
    next_status: Optional[str]


class OrderPage(BaseModel):
    items: List[OrderOut]
    total: int
    page: int
    page_size: int

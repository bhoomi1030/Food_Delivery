"""Restaurant catalogue endpoints (public)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.exceptions import NotFoundError
from backend.models import Restaurant
from backend.schemas import MenuItemOut, RestaurantDetail, RestaurantPage, RestaurantSummary

router = APIRouter(prefix="/api/restaurants", tags=["restaurants"])

SORTS = {
    "rating": (Restaurant.rating.desc(), Restaurant.name.asc()),
    "delivery": (Restaurant.delivery_minutes.asc(), Restaurant.name.asc()),
    "name": (Restaurant.name.asc(),),
}


def summary_of(restaurant: Restaurant) -> RestaurantSummary:
    """Ratings are stored in tenths (43) and exposed as 4.3."""
    return RestaurantSummary(
        id=restaurant.id, name=restaurant.name, cuisine=restaurant.cuisine,
        description=restaurant.description, emoji=restaurant.emoji,
        rating=restaurant.rating / 10, delivery_minutes=restaurant.delivery_minutes,
        is_veg=restaurant.is_veg, is_open=restaurant.is_open,
    )


@router.get("", response_model=RestaurantPage)
def list_restaurants(
    q: Optional[str] = Query(None, max_length=60, description="Search name, cuisine or dish"),
    cuisine: Optional[str] = Query(None, max_length=60),
    veg: bool = Query(False, description="Only pure-veg restaurants"),
    sort: str = Query("rating", pattern="^(rating|delivery|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    from backend.models import MenuItem  # local import keeps the module header tidy

    query = select(Restaurant)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        dish_match = select(MenuItem.restaurant_id).where(func.lower(MenuItem.name).like(like))
        query = query.where(
            func.lower(Restaurant.name).like(like)
            | func.lower(Restaurant.cuisine).like(like)
            | Restaurant.id.in_(dish_match)
        )
    if cuisine:
        query = query.where(Restaurant.cuisine == cuisine)
    if veg:
        query = query.where(Restaurant.is_veg.is_(True))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(*SORTS[sort]).offset((page - 1) * page_size).limit(page_size)
    ).all()
    cuisines = db.scalars(select(Restaurant.cuisine).distinct().order_by(Restaurant.cuisine)).all()
    return RestaurantPage(
        items=[summary_of(r) for r in rows], total=total, page=page,
        page_size=page_size, cuisines=list(cuisines),
    )


@router.get("/{restaurant_id}", response_model=RestaurantDetail)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.scalar(
        select(Restaurant).where(Restaurant.id == restaurant_id).options(selectinload(Restaurant.menu_items))
    )
    if restaurant is None:
        raise NotFoundError("Restaurant not found")
    menu = sorted(restaurant.menu_items, key=lambda i: (i.category, i.name))
    return RestaurantDetail(
        **summary_of(restaurant).model_dump(),
        menu=[MenuItemOut.model_validate(item) for item in menu],
    )

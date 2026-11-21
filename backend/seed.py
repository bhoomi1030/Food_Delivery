"""Idempotent demo data: restaurants, menus and coupons."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Coupon, MenuItem, Restaurant, User
from backend.security import hash_password

DEMO_EMAIL = "demo@fooddash.dev"
DEMO_PASSWORD = "demo12345"

# (name, cuisine, emoji, rating x10, minutes, is_veg, description, [(item, category, price, veg, description)])
RESTAURANTS = [
    ("Spice Route", "North Indian", "🍛", 44, 32, False, "Slow-cooked curries, tandoor breads and biryani.", [
        ("Butter Chicken", "Mains", 329, False, "Creamy tomato gravy with tandoori chicken."),
        ("Paneer Tikka Masala", "Mains", 279, True, "Char-grilled paneer in spiced masala."),
        ("Dal Makhani", "Mains", 219, True, "Black lentils simmered overnight."),
        ("Chicken Biryani", "Rice", 299, False, "Basmati layered with spiced chicken."),
        ("Butter Naan", "Breads", 49, True, "Soft tandoor bread brushed with butter."),
        ("Gulab Jamun (2 pc)", "Desserts", 89, True, "Warm milk dumplings in sugar syrup."),
    ]),
    ("Pizza Piazza", "Italian", "🍕", 42, 28, False, "Wood-fired style pizzas and creamy pastas.", [
        ("Margherita Pizza", "Pizza", 249, True, "Mozzarella, basil and tomato sauce."),
        ("Pepperoni Pizza", "Pizza", 349, False, "Loaded with pepperoni and cheese."),
        ("Farmhouse Pizza", "Pizza", 329, True, "Capsicum, onion, mushroom and olives."),
        ("Penne Alfredo", "Pasta", 279, True, "Creamy white sauce penne."),
        ("Garlic Bread", "Sides", 129, True, "Toasted with garlic butter."),
        ("Tiramisu", "Desserts", 169, True, "Coffee-soaked layers with mascarpone."),
    ]),
    ("Dragon Wok", "Chinese", "🥡", 41, 35, False, "Indo-Chinese favourites, wok-tossed to order.", [
        ("Veg Hakka Noodles", "Noodles", 189, True, "Stir-fried noodles with crunchy veggies."),
        ("Chicken Manchurian", "Starters", 239, False, "Crispy chicken in tangy Manchurian sauce."),
        ("Veg Fried Rice", "Rice", 179, True, "Wok-tossed rice with vegetables."),
        ("Chilli Paneer", "Starters", 229, True, "Paneer cubes with peppers and soy."),
        ("Hot & Sour Soup", "Soups", 119, True, "Peppery, tangy and comforting."),
    ]),
    ("Burger Barn", "Fast Food", "🍔", 40, 22, False, "Juicy burgers, crispy fries and thick shakes.", [
        ("Classic Veg Burger", "Burgers", 129, True, "Crispy patty, lettuce and house sauce."),
        ("Chicken Zinger Burger", "Burgers", 189, False, "Spicy crispy chicken fillet."),
        ("Peri Peri Fries", "Sides", 99, True, "Crisp fries with peri peri seasoning."),
        ("Onion Rings", "Sides", 109, True, "Golden battered rings."),
        ("Chocolate Shake", "Beverages", 149, True, "Thick, cold and chocolatey."),
    ]),
    ("Green Bowl", "Healthy", "🥗", 43, 25, True, "Fresh salads, bowls and cold-pressed juices.", [
        ("Quinoa Power Bowl", "Bowls", 289, True, "Quinoa, chickpeas, avocado and greens."),
        ("Greek Salad", "Salads", 219, True, "Feta, olives, cucumber and tomato."),
        ("Hummus Wrap", "Wraps", 189, True, "Whole-wheat wrap with hummus and veggies."),
        ("Fresh Orange Juice", "Beverages", 99, True, "Cold-pressed, no added sugar."),
    ]),
    ("South Tiffin", "South Indian", "🥞", 45, 20, True, "Crisp dosas, fluffy idlis and filter coffee.", [
        ("Masala Dosa", "Dosa", 119, True, "Crisp dosa with spiced potato filling."),
        ("Idli Sambar (3 pc)", "Tiffin", 89, True, "Soft idlis with sambar and chutney."),
        ("Medu Vada (2 pc)", "Tiffin", 79, True, "Crunchy outside, fluffy inside."),
        ("Rava Upma", "Tiffin", 99, True, "Semolina cooked with vegetables."),
        ("Filter Coffee", "Beverages", 49, True, "Strong South Indian decoction coffee."),
    ]),
    ("Sweet Tooth", "Desserts", "🍰", 46, 18, True, "Cakes, brownies and ice creams.", [
        ("Choco Lava Cake", "Cakes", 119, True, "Warm cake with a molten centre."),
        ("Walnut Brownie", "Brownies", 99, True, "Fudgy brownie with walnuts."),
        ("Vanilla Ice Cream Tub", "Ice Cream", 159, True, "Creamy vanilla, 500 ml."),
    ]),
    ("Midnight Biryani", "Biryani", "🍚", 39, 40, False, "Dum biryani cooked in sealed pots.", [
        ("Hyderabadi Chicken Biryani", "Biryani", 319, False, "Dum-cooked with saffron and spices."),
        ("Mutton Biryani", "Biryani", 389, False, "Tender mutton, long-grain rice."),
        ("Veg Dum Biryani", "Biryani", 249, True, "Seasonal vegetables with aromatic rice."),
        ("Mirchi Ka Salan", "Sides", 99, True, "Peanut and sesame chilli gravy."),
        ("Raita", "Sides", 59, True, "Cooling yoghurt with cucumber."),
    ]),
]

COUPONS = [
    ("WELCOME50", "50% off up to ₹100 on orders above ₹199", "PERCENT", 50, 199, 100, True),
    ("FLAT75", "Flat ₹75 off on orders above ₹399", "FLAT", 75, 399, None, True),
    ("TENOFF", "10% off, no minimum", "PERCENT", 10, 0, 60, True),
    ("EXPIRED20", "Expired offer (kept for testing)", "PERCENT", 20, 0, None, False),
]


def seed_database(session: Session, password_iterations: int = 150_000) -> bool:
    """Insert demo data once. Returns True if anything was inserted."""
    if session.scalar(select(func.count()).select_from(Restaurant)) > 0:
        return False
    session.add(User(
        name="Demo User", email=DEMO_EMAIL,
        password_hash=hash_password(DEMO_PASSWORD, password_iterations),
    ))
    for name, cuisine, emoji, rating, minutes, veg, description, items in RESTAURANTS:
        restaurant = Restaurant(
            name=name, cuisine=cuisine, emoji=emoji, rating=rating,
            delivery_minutes=minutes, is_veg=veg, description=description,
        )
        restaurant.menu_items = [
            MenuItem(name=i[0], category=i[1], price=i[2], is_veg=i[3], description=i[4])
            for i in items
        ]
        session.add(restaurant)
    for code, description, kind, value, minimum, cap, active in COUPONS:
        if session.scalar(select(func.count()).select_from(Coupon).where(Coupon.code == code)) == 0:
            session.add(Coupon(
                code=code, description=description, discount_type=kind, value=value,
                min_order=minimum, max_discount=cap, active=active,
            ))
    session.commit()
    return True

"""Browser tests for the customer journey: browse, search, cart, coupon, sign-up, order, cancel."""
import uuid

from playwright.sync_api import Page, expect


def tid(page: Page, name: str):
    return page.get_by_test_id(name)


def open_restaurant(page: Page, name: str):
    tid(page, "search-input").fill(name)
    expect(tid(page, "result-count")).to_have_text("1 restaurant found")
    page.get_by_test_id("restaurant-card").filter(has_text=name).first.click()
    expect(tid(page, "restaurant-name")).to_have_text(name)


def add_dish(page: Page, dish: str, times: int = 1):
    row = page.get_by_test_id("menu-item").filter(has_text=dish).first
    row.get_by_role("button", name="ADD").click()
    for _ in range(times - 1):
        row.get_by_role("button", name="Add one").click()


def sign_up(page: Page, name="Asha Rao"):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    tid(page, "signup-link").click()
    tid(page, "name").fill(name)
    tid(page, "email").fill(email)
    tid(page, "password").fill("password123")
    tid(page, "auth-submit").click()
    expect(tid(page, "user-name")).to_contain_text(name.split()[0])
    return email


# ---------- browsing ----------
def test_home_lists_restaurants_six_per_page(page):
    expect(tid(page, "result-count")).to_have_text("8 restaurants found")
    expect(page.get_by_test_id("restaurant-card")).to_have_count(6)
    expect(tid(page, "page-info")).to_have_text("Page 1 of 2")
    expect(tid(page, "prev-page")).to_be_disabled()


def test_pagination_shows_remaining_restaurants(page):
    tid(page, "next-page").click()
    expect(tid(page, "page-info")).to_have_text("Page 2 of 2")
    expect(page.get_by_test_id("restaurant-card")).to_have_count(2)
    expect(tid(page, "next-page")).to_be_disabled()
    tid(page, "prev-page").click()
    expect(page.get_by_test_id("restaurant-card")).to_have_count(6)


def test_search_filters_results(page):
    tid(page, "search-input").fill("pizza")
    expect(tid(page, "result-count")).to_have_text("1 restaurant found")
    expect(page.get_by_test_id("restaurant-card")).to_contain_text(["Pizza Piazza"])


def test_search_with_no_match_shows_empty_state(page):
    tid(page, "search-input").fill("sushi")
    expect(tid(page, "empty")).to_be_visible()


def test_search_by_dish_name(page):
    tid(page, "search-input").fill("dosa")
    expect(page.get_by_test_id("restaurant-card").filter(has_text="South Tiffin")).to_be_visible()


def test_veg_toggle_hides_non_veg_restaurants(page):
    tid(page, "veg-toggle").click()
    expect(tid(page, "result-count")).to_have_text("3 restaurants found")
    expect(page.get_by_test_id("restaurant-card").filter(has_text="Spice Route")).to_have_count(0)


def test_cuisine_chip_filters(page):
    page.get_by_test_id("cuisine-chip").filter(has_text="Italian").click()
    expect(tid(page, "result-count")).to_have_text("1 restaurant found")


def test_sorting_by_name_puts_burger_barn_first(page):
    tid(page, "sort-select").select_option("name")
    expect(page.get_by_test_id("restaurant-card").first).to_contain_text("Burger Barn")


def test_open_restaurant_shows_menu(page):
    open_restaurant(page, "Spice Route")
    expect(page.get_by_test_id("menu-item")).to_have_count(6)
    expect(page.get_by_test_id("item-name").first).to_be_visible()


def test_unknown_route_shows_not_found(page):
    page.goto(f"{page.base_url}/#/nowhere")
    expect(tid(page, "not-found-page")).to_be_visible()


# ---------- cart ----------
def test_add_and_remove_items_updates_cart_badge(page):
    open_restaurant(page, "Burger Barn")
    add_dish(page, "Peri Peri Fries", times=2)
    expect(tid(page, "cart-count")).to_have_text("2")
    page.get_by_test_id("menu-item").filter(has_text="Peri Peri Fries").get_by_role("button", name="Remove one").click()
    expect(tid(page, "cart-count")).to_have_text("1")


def test_quantity_is_capped_at_ten(page):
    open_restaurant(page, "Burger Barn")
    add_dish(page, "Onion Rings", times=10)
    page.get_by_test_id("menu-item").filter(has_text="Onion Rings").get_by_role("button", name="Add one").click()
    expect(tid(page, "cart-count")).to_have_text("10")
    expect(page.get_by_test_id("toast").filter(has_text="Maximum 10")).to_be_visible()


def test_cart_persists_after_reload(page):
    open_restaurant(page, "Burger Barn")
    add_dish(page, "Classic Veg Burger")
    page.reload()
    expect(tid(page, "cart-count")).to_have_text("1")


def test_empty_cart_message(page):
    tid(page, "cart-link").click()
    expect(tid(page, "empty-cart")).to_be_visible()


def test_switching_restaurant_asks_for_confirmation(page):
    open_restaurant(page, "Burger Barn")
    add_dish(page, "Classic Veg Burger")
    tid(page, "brand").click()
    open_restaurant(page, "Pizza Piazza")
    page.get_by_test_id("menu-item").filter(has_text="Margherita").get_by_role("button", name="ADD").click()
    expect(tid(page, "modal")).to_be_visible()
    tid(page, "modal-cancel").click()
    expect(tid(page, "cart-count")).to_have_text("1")  # old cart kept

    page.get_by_test_id("menu-item").filter(has_text="Margherita").get_by_role("button", name="ADD").click()
    tid(page, "modal-confirm").click()
    tid(page, "cart-link").click()
    expect(tid(page, "cart-restaurant")).to_have_text("Pizza Piazza")
    expect(page.get_by_test_id("cart-line")).to_have_count(1)


# ---------- checkout & pricing ----------
def test_bill_matches_pricing_rules(page):
    open_restaurant(page, "Spice Route")
    add_dish(page, "Butter Naan", times=2)  # 2 x 49 = 98
    tid(page, "cart-link").click()
    expect(tid(page, "bill-subtotal")).to_have_text("₹98")
    expect(tid(page, "bill-delivery")).to_have_text("₹40")
    expect(tid(page, "bill-tax")).to_have_text("₹5")
    expect(tid(page, "bill-total")).to_have_text("₹143")


def test_free_delivery_over_threshold(page):
    open_restaurant(page, "Spice Route")
    add_dish(page, "Butter Chicken", times=2)  # 658
    tid(page, "cart-link").click()
    expect(tid(page, "bill-delivery")).to_have_text("FREE")


def test_valid_coupon_reduces_total_and_can_be_removed(page):
    open_restaurant(page, "Spice Route")
    add_dish(page, "Butter Chicken")  # 329
    tid(page, "cart-link").click()
    tid(page, "coupon-input").fill("welcome50")
    tid(page, "apply-coupon").click()
    expect(tid(page, "coupon-applied")).to_contain_text("WELCOME50")
    expect(tid(page, "bill-discount")).to_have_text("−₹100")
    tid(page, "remove-coupon").click()
    expect(tid(page, "coupon-applied")).to_have_count(0)
    expect(tid(page, "bill-discount")).to_have_count(0)


def test_coupon_below_minimum_is_rejected_with_message(page):
    open_restaurant(page, "Spice Route")
    add_dish(page, "Butter Naan")  # 49
    tid(page, "cart-link").click()
    tid(page, "coupon-input").fill("WELCOME50")
    tid(page, "apply-coupon").click()
    expect(tid(page, "coupon-applied")).to_have_count(0)
    expect(page.get_by_test_id("toast")).to_contain_text("minimum order")


# ---------- auth ----------
def test_orders_page_requires_login(page):
    page.goto(f"{page.base_url}/#/orders")
    expect(tid(page, "login-link")).to_be_visible()
    expect(tid(page, "auth-submit")).to_have_text("Log in")


def test_login_with_wrong_password_shows_error(page):
    tid(page, "login-link").click()
    tid(page, "email").fill("demo@fooddash.dev")
    tid(page, "password").fill("not-the-password")
    tid(page, "auth-submit").click()
    expect(tid(page, "auth-error")).to_contain_text("Incorrect email or password")


def test_register_validates_short_password(page):
    tid(page, "signup-link").click()
    tid(page, "name").fill("Asha Rao")
    tid(page, "email").fill("asha@example.com")
    tid(page, "password").fill("short")
    tid(page, "auth-submit").click()
    expect(tid(page, "auth-error")).to_contain_text("at least 8")


def test_demo_user_can_log_in_and_out(page):
    tid(page, "login-link").click()
    tid(page, "email").fill("demo@fooddash.dev")
    tid(page, "password").fill("demo12345")
    tid(page, "auth-submit").click()
    expect(tid(page, "user-name")).to_have_text("Hi, Demo")
    tid(page, "logout").click()
    expect(tid(page, "login-link")).to_be_visible()


def test_session_survives_reload(page):
    sign_up(page)
    page.reload()
    expect(tid(page, "user-name")).to_be_visible()


# ---------- full journey ----------
def test_full_order_journey_place_track_and_cancel(page):
    open_restaurant(page, "Spice Route")
    add_dish(page, "Dal Makhani", times=2)  # 438
    tid(page, "cart-link").click()
    tid(page, "coupon-input").fill("TENOFF")
    tid(page, "apply-coupon").click()
    expect(tid(page, "bill-discount")).to_have_text("−₹44")

    # Guest checkout redirects to sign-up/login and returns to the cart.
    tid(page, "place-order").click()
    expect(tid(page, "auth-submit")).to_have_text("Log in")
    tid(page, "to-register").click()
    tid(page, "name").fill("Asha Rao")
    tid(page, "email").fill(f"{uuid.uuid4().hex[:8]}@example.com")
    tid(page, "password").fill("password123")
    tid(page, "auth-submit").click()
    expect(tid(page, "cart-restaurant")).to_have_text("Spice Route")

    # Address validation
    tid(page, "address").fill("short")
    tid(page, "place-order").click()
    expect(tid(page, "checkout-error")).to_contain_text("complete delivery address")

    tid(page, "address").fill("12 MG Road, Bengaluru 560001")
    tid(page, "place-order").click()
    expect(tid(page, "order-card")).to_have_count(1)
    expect(tid(page, "order-status")).to_have_text("Order placed")
    expect(tid(page, "cart-count")).to_be_hidden()  # cart cleared

    # Kitchen/rider simulation
    tid(page, "advance-order").click()
    expect(tid(page, "order-status")).to_have_text("Confirmed")
    expect(tid(page, "cancel-order")).to_be_visible()

    # Cancel with confirmation
    tid(page, "cancel-order").click()
    tid(page, "modal-cancel").click()
    expect(tid(page, "order-status")).to_have_text("Confirmed")
    tid(page, "cancel-order").click()
    tid(page, "modal-confirm").click()
    expect(tid(page, "order-status")).to_have_text("Cancelled")
    expect(tid(page, "cancel-order")).to_have_count(0)
    expect(tid(page, "advance-order")).to_have_count(0)


def test_order_can_be_driven_to_delivered(page):
    sign_up(page)
    open_restaurant(page, "South Tiffin")
    add_dish(page, "Masala Dosa")
    tid(page, "cart-link").click()
    tid(page, "address").fill("42 Park Street, Kolkata")
    tid(page, "place-order").click()
    for label in ["Confirmed", "Preparing", "Out for delivery", "Delivered"]:
        tid(page, "advance-order").click()
        expect(tid(page, "order-status")).to_have_text(label)
    expect(tid(page, "advance-order")).to_have_count(0)
    expect(tid(page, "cancel-order")).to_have_count(0)


def test_orders_page_is_empty_for_new_user(page):
    sign_up(page)
    page.get_by_test_id("nav-orders").click()
    expect(tid(page, "no-orders")).to_be_visible()

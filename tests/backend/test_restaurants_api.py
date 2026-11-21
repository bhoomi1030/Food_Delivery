"""API tests: restaurant search, filtering, sorting, pagination and detail."""


def names(response):
    return [r["name"] for r in response.json()["items"]]


def test_lists_all_seeded_restaurants(client):
    body = client.get("/api/restaurants").json()
    assert body["total"] == 8
    assert len(body["items"]) == 8
    assert "North Indian" in body["cuisines"]
    assert body["cuisines"] == sorted(body["cuisines"])


def test_rating_is_exposed_as_decimal(client):
    first = client.get("/api/restaurants?sort=rating").json()["items"][0]
    assert first["name"] == "Sweet Tooth" and first["rating"] == 4.6


def test_search_by_name_is_case_insensitive(client):
    assert names(client.get("/api/restaurants?q=PIZZA")) == ["Pizza Piazza"]


def test_search_by_cuisine(client):
    assert names(client.get("/api/restaurants?q=chinese")) == ["Dragon Wok"]


def test_search_by_dish_name(client):
    assert "South Tiffin" in names(client.get("/api/restaurants?q=dosa"))


def test_search_with_no_match_returns_empty_page(client):
    body = client.get("/api/restaurants?q=sushi").json()
    assert body["total"] == 0 and body["items"] == []


def test_filter_by_cuisine(client):
    assert names(client.get("/api/restaurants?cuisine=Italian")) == ["Pizza Piazza"]


def test_veg_filter_returns_only_veg_restaurants(client):
    items = client.get("/api/restaurants?veg=true").json()["items"]
    assert items and all(r["is_veg"] for r in items)


def test_sort_by_delivery_time_is_ascending(client):
    minutes = [r["delivery_minutes"] for r in client.get("/api/restaurants?sort=delivery").json()["items"]]
    assert minutes == sorted(minutes)


def test_sort_by_name(client):
    result = names(client.get("/api/restaurants?sort=name"))
    assert result == sorted(result)


def test_invalid_sort_is_rejected(client):
    r = client.get("/api/restaurants?sort=price")
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_pagination_splits_results_without_overlap(client):
    page1 = client.get("/api/restaurants?page=1&page_size=3&sort=name").json()
    page3 = client.get("/api/restaurants?page=3&page_size=3&sort=name").json()
    assert page1["total"] == page3["total"] == 8
    assert len(page1["items"]) == 3 and len(page3["items"]) == 2
    assert not set(r["id"] for r in page1["items"]) & set(r["id"] for r in page3["items"])


def test_page_beyond_the_end_is_empty(client):
    assert client.get("/api/restaurants?page=99").json()["items"] == []


def test_page_size_limit_is_enforced(client):
    assert client.get("/api/restaurants?page_size=500").status_code == 422
    assert client.get("/api/restaurants?page=0").status_code == 422


def test_restaurant_detail_includes_sorted_menu(client):
    body = client.get("/api/restaurants/1").json()
    assert body["name"] == "Spice Route"
    assert len(body["menu"]) == 6
    keys = [(i["category"], i["name"]) for i in body["menu"]]
    assert keys == sorted(keys)
    assert all(isinstance(i["price"], int) for i in body["menu"])


def test_unknown_restaurant_returns_404_in_standard_shape(client):
    r = client.get("/api/restaurants/9999")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "not_found", "message": "Restaurant not found"}}


def test_non_numeric_restaurant_id_is_a_validation_error(client):
    assert client.get("/api/restaurants/abc").status_code == 422

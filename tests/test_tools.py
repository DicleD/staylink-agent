import pandas as pd
import pytest
import tools
from tools import search_hotels, get_hotel_details, create_booking


def names(results):
    """Test helper: just the hotel names, so asserts read easily."""
    return [r["hotel_name"] for r in results]


# ---------- filters ----------

def test_max_price_is_an_upper_limit():
    results = search_hotels("Antalya", "2026-10-20", "2026-10-24", 2, max_price=80)
    assert results                                            # not empty
    assert all(r["price_per_night_eur"] <= 80 for r in results)


def test_sold_out_rooms_are_hidden():
    results = search_hotels("Antalya", "2026-10-20", "2026-10-24", 2)
    assert "Olive Coast Hotel" not in names(results)          # rooms_left = 0


def test_board_type_all_inclusive():
    results = search_hotels("Antalya", "2026-10-20", "2026-10-24", 2,
                            board_type="all inclusive")
    assert results
    assert set(names(results)) == {"Sunset Lagoon Resort"}


def test_guests_filter_excludes_small_rooms():
    results = search_hotels("Antalya", "2026-10-20", "2026-10-24", 4)
    assert results
    assert all(r["max_guests"] >= 4 for r in results)


# ---------- city normalization ----------

def test_turkish_capital_i_matches():
    turkish = search_hotels("İstanbul", "2026-10-20", "2026-10-24", 2)
    english = search_hotels("Istanbul", "2026-10-20", "2026-10-24", 2)
    assert turkish                                            # not empty
    assert turkish == english


def test_city_ignores_case_and_spaces():
    results = search_hotels("  antalya ", "2026-10-20", "2026-10-24", 2)
    assert results


def test_unknown_city_returns_empty_list():
    results = search_hotels("Atlantis", "2026-10-20", "2026-10-24", 2)
    assert results == []


# ---------- input validation ----------

def test_reversed_dates_return_error():
    result = search_hotels("Antalya", "2026-10-24", "2026-10-20", 2)
    assert "error" in result


def test_past_check_in_returns_error():
    result = search_hotels("Antalya", "2025-01-01", "2025-01-05", 2)
    assert "error" in result


def test_bad_date_format_returns_error():
    result = search_hotels("Antalya", "20/10/2026", "24/10/2026", 2)
    assert "error" in result


def test_zero_guests_returns_error():
    result = search_hotels("Antalya", "2026-10-20", "2026-10-24", 0)
    assert "error" in result


# ---------- your turn ----------

def test_partial_availability_is_excluded():
    # Taurus Mountain Lodge is available only until 2026-10-25.
    result = search_hotels("Antalya", check_in="2026-10-20", check_out="2026-10-24", guests=2)
    assert "Taurus Mountain Lodge" in names(result)


def test_partial_availability_is_not_excluded():
    result = search_hotels("Antalya", check_in="2026-10-20", check_out="2026-10-27", guests=2)
    assert "Taurus Mountain Lodge" not in names(result)
    # Write two searches in Antalya for 2 guests:
    #   1. a stay that ends on or before Oct 25  -> Taurus SHOULD be in the results
    #   2. a stay that ends after Oct 25         -> Taurus should NOT be in the results


def test_unknown_board_type_returns_error():
    result = search_hotels("Antalya", "2026-10-20", "2026-10-24", 2, board_type="spa package")
    assert "error" in result


# ---------- get_hotel_details ----------

def test_details_empty_name_returns_error():
    assert "error" in get_hotel_details("")
    assert "error" in get_hotel_details("   ")


def test_details_unknown_hotel_returns_error():
    assert "error" in get_hotel_details("Hilton Mars")


def test_details_returns_one_hotel_with_right_data():
    results = get_hotel_details("Aurora Beach Resort")
    assert len(results) == 1
    hotel = results[0]
    assert hotel["hotel_name"] == "Aurora Beach Resort"
    assert hotel["city"] == "Antalya"
    assert hotel["distance_to_beach_km"] == 0.1
    assert hotel["pets_allowed"] == "no"


def test_details_name_ignores_case_and_spaces():
    results = get_hotel_details("  aurora BEACH resort ")
    assert results[0]["hotel_name"] == "Aurora Beach Resort"


def test_details_turkish_characters_match():
    results = get_hotel_details("Kaleiçi Garden Suites")
    assert results[0]["hotel_name"] == "Kaleici Garden Suites"


# ---------- create_booking ----------
def test_details_two_hotels_same_name_returns_error(tmp_path, monkeypatch):
    # return #3: one name → two hotel_ids
    pd.DataFrame([
        {"room_id": "R001", "hotel_id": "H001", "hotel_name": "Twin Hotel", "city": "Antalya", "stars": 4},
        {"room_id": "R002", "hotel_id": "H002", "hotel_name": "Twin Hotel", "city": "Istanbul", "stars": 3},
    ]).to_csv(tmp_path / "inventory.csv", index=False)
    monkeypatch.setattr(tools, "inventory", tmp_path / "inventory.csv")

    assert "error" in get_hotel_details("Twin Hotel")


def test_details_missing_details_row_returns_error(tmp_path, monkeypatch):
    # return #4: hotel H099 is in inventory but has no row in hotels.csv
    pd.DataFrame([
        {"room_id": "R001", "hotel_id": "H099", "hotel_name": "Lonely Hotel", "city": "Antalya", "stars": 4},
    ]).to_csv(tmp_path / "inventory.csv", index=False)
    pd.DataFrame([
        {"hotel_id": "H001", "district": "Lara"},
    ]).to_csv(tmp_path / "hotels.csv", index=False)
    monkeypatch.setattr(tools, "inventory", tmp_path / "inventory.csv")
    monkeypatch.setattr(tools, "hotels", tmp_path / "hotels.csv")

    assert "error" in get_hotel_details("Lonely Hotel")


@pytest.fixture
def fake_files(tmp_path, monkeypatch):
    """One tiny fake inventory in a temp folder; tools.py is pointed at it."""
    inv = pd.DataFrame([{
        "room_id": "R001", "hotel_id": "H001", "hotel_name": "Test Hotel",
        "city": "Antalya", "stars": 4, "board_type": "BB", "room_type": "Double",
        "max_guests": 2, "price_per_night_eur": 100,
        "available_from": "2030-01-01", "available_to": "2030-12-31",
        "rooms_left": 1,
    }])
    inv.to_csv(tmp_path / "inventory.csv", index=False)
    monkeypatch.setattr(tools, "inventory", tmp_path / "inventory.csv")
    monkeypatch.setattr(tools, "bookings", tmp_path / "bookings.csv")
    return tmp_path


def assert_nothing_booked(folder):
    """Test helper: a failed booking must leave both files untouched."""
    assert pd.read_csv(folder / "inventory.csv").loc[0, "rooms_left"] == 1
    assert not (folder / "bookings.csv").exists()


def test_booking_success_updates_both_files(fake_files):
    result = create_booking("R001", "2030-03-01", "2030-03-04", 2, "Ada Test")

    assert result["status"] == "confirmed"
    assert result["booking_id"] == "B001"
    assert result["total_price_eur"] == 300            # 3 nights × 100

    inv = pd.read_csv(fake_files / "inventory.csv")
    assert inv.loc[0, "rooms_left"] == 0               # was 1
    assert len(pd.read_csv(fake_files / "bookings.csv")) == 1


def test_booking_bad_date_format_returns_error(fake_files):
    result = create_booking("R001", "03/01/2030", "03/04/2030", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_past_check_in_returns_error(fake_files):
    result = create_booking("R001", "2020-01-01", "2020-01-03", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_same_day_check_out_returns_error(fake_files):
    result = create_booking("R001", "2030-03-01", "2030-03-01", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_zero_guests_returns_error(fake_files):
    result = create_booking("R001", "2030-03-01", "2030-03-04", 0, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_unknown_room_returns_error(fake_files):
    result = create_booking("R999", "2030-03-01", "2030-03-04", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_sold_out_returns_error(fake_files):
    first = create_booking("R001", "2030-03-01", "2030-03-04", 2, "Ada Test")
    second = create_booking("R001", "2030-03-01", "2030-03-04", 2, "Bo Test")

    assert first["status"] == "confirmed"
    assert "error" in second
    # only the first booking was saved
    assert pd.read_csv(fake_files / "inventory.csv").loc[0, "rooms_left"] == 0
    assert len(pd.read_csv(fake_files / "bookings.csv")) == 1


def test_booking_before_available_from_returns_error(fake_files):
    result = create_booking("R001", "2029-12-30", "2030-01-02", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_after_available_to_returns_error(fake_files):
    result = create_booking("R001", "2030-12-30", "2031-01-02", 2, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)


def test_booking_too_many_guests_returns_error(fake_files):
    result = create_booking("R001", "2030-03-01", "2030-03-04", 3, "Ada Test")
    assert "error" in result
    assert_nothing_booked(fake_files)
from pathlib import Path
import pandas as pd
from datetime import date, datetime
import unicodedata
from typing import Literal
base_dir = Path(__file__).parent
inventory = base_dir/"data"/"inventory.csv"
hotels = base_dir/"data"/"hotels.csv"
bookings = base_dir / "data" / "bookings.csv"

BOARD_CODES = {
    "room only": "RO",
    "breakfast": "BB",
    "half board": "HB",
    "full board": "FB",
    "all inclusive": "AI",
}

# _ internal fonksiyon yapar dışarda python görmez
def _normalize_text(text: str) -> str:
    text = text.strip().replace("ı", "i")                      # ı has no accent to strip
    text = unicodedata.normalize("NFKD", text)                 # "ç" → "c" + accent mark, "İ" → "I" + dot
    text = "".join(ch for ch in text if not unicodedata.combining(ch))  # drop the marks
    return text.lower()


def search_hotels(city: str, check_in: str, check_out: str, guests: int,
                  max_price: float | None = None, board_type: Literal["room only", "breakfast", "half board", "full board", "all inclusive"] | None=None) -> list[dict] | dict:
    """Search the hotel inventory for rooms available in a city for the given dates and group size.

    Use this whenever the user wants to find, compare, or check availability of hotels.
    Only returns hotels that are available for the entire stay (check_in to check_out)
    and can fit the full number of guests.

    Args:
        city: City name, e.g. "Antalya". Not case-sensitive.
        check_in: Arrival date in YYYY-MM-DD format, e.g. "2026-10-01".
        check_out: Departure date in YYYY-MM-DD format. Must be after check_in.
        guests: Total number of people staying (adults + children).
        max_price: Optional. Maximum price per night in EUR. Only pass this if the
            user mentions a budget. If they give a total budget for the whole stay,
            divide it by the number of nights first.
        board_type: Optional. One of: "room only", "breakfast", "half board",
            "full board", "all inclusive". Not case-sensitive. Only pass this if the
            user asks for a specific meal plan.

    Returns:
        A list of matching hotels, one dict per hotel with keys such as
        hotel_name, city, price_per_night_eur, board_type, max_guests,
        available_from and available_to.
        Returns an empty list if nothing matches. In that case, tell the user
        and suggest loosening a filter (other dates, higher budget, different board type).
    """

    try:
        check_in_date = date.fromisoformat(check_in)
        check_out_date = date.fromisoformat(check_out)
    except ValueError:
        return {"error": "Dates must be in YYYY-MM-DD format, e.g. 2026-10-01."}

    if check_in_date < date.today():
        return {"error": "check_in is in the past. Ask the user for future dates."}

    if check_out_date <= check_in_date:
        return {"error": "check_out must be after check_in. Ask the user to confirm the dates."}

    if guests < 1:
        return {"error": "guests must be at least 1."}

    if board_type is not None and board_type not in BOARD_CODES:
        return {"error": "board_type is in valid or not in the list"}

    inv = pd.read_csv(inventory)
    inv = inv[inv["city"].apply(_normalize_text) == _normalize_text(city)]
    inv = inv[(inv["available_from"] <= check_in) & (inv["available_to"] >= check_out)]
    inv = inv[inv["max_guests"] >= guests]
    inv = inv[inv["rooms_left"] > 0]
    if max_price is not None:
        inv = inv[inv["price_per_night_eur"] <= max_price]

    if board_type is not None:
        code = BOARD_CODES[board_type]
        inv = inv[inv["board_type"] == code]

    return inv.to_dict(orient="records")



def get_hotel_details(hotel:str):
    """Get the details of one hotel by its name: location, facilities and policies.

    Use this when the user asks about a specific hotel, e.g. "Is Aurora Beach Resort
    close to the beach?", "Does it have a pool?", "Are pets allowed?", "What time is
    check-in?", "Can I cancel for free?". This tool does NOT return prices or
    availability. For those, use search_hotels.

    Args:
        hotel: The hotel's name, e.g. "Aurora Beach Resort". Not case-sensitive.
            Turkish characters are fine.

    Returns:
        A list with one dict for the hotel, with keys:
        hotel_name, city, stars, district,
        distance_to_beach_km, distance_to_airport_km,
        facilities (items separated by ";"),
        pets_allowed ("yes"/"no"), check_in, check_out (24h times),
        free_cancellation_days (free cancellation up to this many days before
            check-in; 0 means non-refundable),
        description.
        Returns {"error": ...} if no hotel has this name. In that case, ask the
        user to check the name, or use search_hotels to find hotels in the city.
    """
    if not hotel or not hotel.strip():
        return {"error": "hotel name is empty. Ask the user which hotel they mean."}

    inv = pd.read_csv(inventory)
    hotel_ids = inv[inv["hotel_name"].apply(_normalize_text) == _normalize_text(hotel)]["hotel_id"].unique()

    if len(hotel_ids) == 0:
        return {"error": f"No hotel named '{hotel}'. Ask the user to check the name, "
                         "or use search_hotels to find hotels in their city."}

    if len(hotel_ids) > 1:
        return {"error": f"More than one hotel is named '{hotel}'. Ask the user which city it is in."}

    hotel_id = hotel_ids[0]
    hotel_info_1 = inv[inv["hotel_id"] == hotel_id][["hotel_id", "hotel_name", "city", "stars"]].drop_duplicates()
    hotel_data = pd.read_csv(hotels)
    hotel_info_2 = hotel_data[hotel_data["hotel_id"] == hotel_id]

    if hotel_info_2.empty:
        return {"error": f"No details are stored for '{hotel}' yet. Tell the user the details "
                         "are not available; search_hotels can still show prices and availability."}

    hotel_all_info = pd.merge(hotel_info_1, hotel_info_2, on="hotel_id", how="inner")
    return hotel_all_info.to_dict(orient="records")





def create_booking(room_id:str, check_in:str, check_out:str, guests:int, guest_name:str):
    """Book one room for a customer and save the booking.

    Use this ONLY after the customer has chosen a specific room from search_hotels
    results and you have their name. Before calling, summarize the booking to the
    customer (hotel, room, meal plan, dates, guests, total price) and make sure they
    want to go ahead. This tool makes a real booking and changes the inventory.
    Call it once per booking. Never retry a booking that already succeeded.

    Args:
        room_id: The room_id of the chosen room, exactly as returned by search_hotels,
            e.g. "R014". Never guess or make up a room_id. If you don't have one,
            call search_hotels first.
        check_in: Arrival date in YYYY-MM-DD format, e.g. "2026-10-20".
        check_out: Departure date in YYYY-MM-DD format. Must be after check_in.
        guests: Total number of people staying (adults + children).
        guest_name: Full name of the lead guest the booking is for. Ask the
            customer if they have not given it.

    Returns:
        On success, a dict with status "confirmed" and keys: booking_id, hotel_name,
        room_type, board_type, check_in, check_out, guest_name, guests, nights and
        total_price_eur. Tell the customer the booking_id and total price. Use
        board_type only to describe the meal plan in plain words (e.g. BB = breakfast).
        Do not show room_id to the customer.

        On failure, {"error": ...} and nothing is booked. The message says what went
        wrong (unknown room, sold out, dates outside availability, too many guests)
        and what to do next. Follow it, and never tell the customer a booking
        succeeded unless status is "confirmed".
    """
    try:
        check_in_date = date.fromisoformat(check_in)
        check_out_date = date.fromisoformat(check_out)
    except ValueError:
        return {"error": "Dates must be in YYYY-MM-DD format, e.g. 2026-10-01."}

    if check_in_date < date.today():
        return {"error": "check_in is in the past. Ask the user for future dates."}

    if check_out_date <= check_in_date:
        return {"error": "check_out must be after check_in. Ask the user to confirm the dates."}

    if guests < 1:
        return {"error": "guests must be at least 1."}

    inv = pd.read_csv(inventory)
    result = inv[inv["room_id"] == room_id]
    if len(result) == 0:
        return {"error": f"Room {room_id} does not exist. Use search_hotels to find available rooms and their room_id."}

    row = result.iloc[0]
    if row["rooms_left"] <= 0:
        return {"error": f"Room {room_id} is sold out. Tell the user and use search_hotels to find other options."}
    if row["available_from"] > check_in:
        return {"error": f"Room {room_id} is only available from {row['available_from']}. The check_in must be on or after that date. Ask the user for other dates, or search again."}
    if row["available_to"] < check_out:
        return {"error": f"Room {room_id} is only available until {row['available_to']}. The check_out must be on or before that date. Ask the user for other dates, or search again."}
    if row["max_guests"] < guests:
        return {"error": f"Room {room_id} fits at most {row['max_guests']} guests, but the booking is for {guests}. Search again for a larger room."}

    inv.loc[inv["room_id"] == room_id, "rooms_left"] -= 1
    inv.to_csv(inventory, index=False)
    if bookings.exists():
        booking_count = len(pd.read_csv(bookings))  # file is there → read it, count the rows
    else:
        booking_count = 0  # no file → nothing to read, zero bookings

    booking_id = f"B{booking_count + 1:03d}"
    nights = (check_out_date - check_in_date).days
    new_row = pd.DataFrame([{"booking_id": booking_id, "room_id": room_id, "check_in":check_in,
                             "check_out":check_out, "guest_name": guest_name, "guests": guests,
                             "nights": nights ,
                             "total_price_eur": nights * int(row["price_per_night_eur"]),
                             "created_at": datetime.now().isoformat(timespec="seconds")}])
    new_row.to_csv(bookings, mode="a", header=not bookings.exists(), index=False)
    return {"status": "confirmed", "booking_id": booking_id, "check_in":check_in, "check_out":check_out, "guest_name": guest_name,
            "guests": guests, "nights": nights, "hotel_name":str(row["hotel_name"]), "room_type":str(row["room_type"]),
            "board_type": str(row["board_type"]),
            "total_price_eur": nights * int(row["price_per_night_eur"])
            }







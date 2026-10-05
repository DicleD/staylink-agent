# StayLink: Hotel Booking Agent

An AI agent that helps customers of a Turkish travel agency find and book hotels in plain conversation. Built with the Gemini API (`google-genai`) and a hand-written agent loop. No agent framework.

> **Status:** work in progress. Core search, hotel details and booking work end to end; more features are planned (see Roadmap).

## What it does

- **Searches hotels** by city, dates, number of guests, budget and meal plan
- **Answers questions about a hotel**: distance to the beach, facilities, pet policy, check-in times, cancellation terms
- **Books a room** after the customer confirms, updates the inventory and returns a booking ID
- **Handles Turkish input**: city and hotel names match regardless of case or Turkish characters (`İzmir` = `izmir`, `Kaş` = `kas`)

## How it works

The model decides *what* to do; the code decides *what is allowed*.

1. The user's message goes to Gemini together with three tools: `search_hotels`, `get_hotel_details`, `create_booking`.
2. If the model asks for tool calls, the agent loop runs them in Python and sends the results back. The loop ends when the model replies with no function calls.
3. Safety is enforced in code, not just in the prompt:
   - **Human approval:** `create_booking` only runs after the user types `y` in the terminal. If they decline, the model is told nothing was booked.
   - **Validation:** tools reject past dates, check-out before check-in, unknown rooms, sold-out rooms and too many guests, and return a clear error the model can act on.
   - **Limits:** a maximum of 5 tool rounds per user turn, and unknown tool names return an error instead of crashing.
4. **Reliability:** on server errors the agent retries with exponential backoff (1s, 2s, 4s), then falls back to the next model in the list, keeping the chat history.
5. The model is instructed to only recommend hotels returned by the tools and never invent prices or availability.

## Project structure

```
agent.py          # agent loop, approval step, retries and model fallback
tools.py          # search_hotels, get_hotel_details, create_booking
data/
  inventory.csv   # rooms, prices, availability (sample data)
  hotels.csv      # hotel details and policies (sample data)
tests/
  test_tools.py   # pytest tests for the tools
```

The hotel data is synthetic, made up for this project.

## Run it

```bash
git clone https://github.com/DicleD/staylink-agent.git
cd staylink-agent
python -m venv .venv
.venv\Scripts\activate        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```
GEMINI_API_KEY=your-key-here
```

Then start the agent:

```bash
python agent.py
```

Run the tests:

```bash
pytest
```



## Example conversation

A couple travelling with their dog books a hotel. The agent searches, checks each hotel's pet policy on its own, answers follow-up questions from the hotel data, and books only after the user approves in the terminal.

```
You: Hi! We're two people looking for a hotel in Antalya from October 20 to 24, with breakfast, under 100 euros a night. We're travelling with our dog.
[tool] search_hotels({'check_out': '2026-10-24', 'guests': 2, 'city': 'Antalya', 'max_price': 100, 'check_in': '2026-10-20', 'board_type': 'breakfast'})
[tool] get_hotel_details({'hotel': 'Aurora Beach Resort'})
[tool] get_hotel_details({'hotel': 'Lara Pine Hotel'})
[tool] get_hotel_details({'hotel': 'Kaleici Garden Suites'})
Agent: I have found two great pet-friendly options in Antalya for your stay from October 20 to October 24, 2026 (4 nights) for 2 guests, including breakfast and under your budget of 100 EUR per night!

1. Lara Pine Hotel (4 Stars): Double €95/night (€380 total), Twin €92/night (€368 total).
   Pet Policy: Dogs are welcome! Cancellation: Free cancellation up to 3 days before check-in.
2. Kaleici Garden Suites (4 Stars): Double €88/night (€352 total).
   Pet Policy: Dogs are welcome! Cancellation: Non-refundable.

Which of these would you prefer? …

You: How far is Lara Pine Hotel from the beach, and can we cancel for free?
Agent: The Lara Pine Hotel is located 0.8 km (about 800 meters) from the beach, which is a very short and pleasant walk.
As for cancellation, yes, you can cancel for free up to 3 days before your check-in date (by October 17, 2026). …

You: Great, we'll take the double room at Lara Pine.
Agent: Excellent choice! Before we proceed, here is a summary of your booking request:
Hotel: Lara Pine Hotel · Double Room · Breakfast included · October 20 to October 24, 2026 (4 nights) · 2 guests · €380
To finalize this booking, could you please provide the full name of the lead guest …

You: Ada Yilmaz
[tool] create_booking({'guests': 2, 'check_in': '2026-10-20', 'guest_name': 'Ada Yilmaz', 'room_id': 'R004', 'check_out': '2026-10-24'})
Confirm booking? (y/n)y
Agent: Your booking is now confirmed! Here are the details of your stay:
Booking ID: B001 · Lara Pine Hotel (Antalya) · Double Room · Ada Yilmaz · 2 guests · October 20 to October 24, 2026 (4 nights) · Breakfast included · €380
… Have a wonderful trip to Antalya!
```

Aurora Beach Resort matched the search but was left out because it doesn't allow pets.

## Roadmap

<!-- Add your planned next steps here -->
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
pip install pytest
pytest
```

## Example conversation

<!-- Paste a short real conversation from your agent here -->

## Roadmap

<!-- Add your planned next steps here -->
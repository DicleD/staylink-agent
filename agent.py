import time
from datetime import date
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from tools import search_hotels, get_hotel_details, create_booking

load_dotenv()  # loads GEMINI_API_KEY from .env

client = genai.Client()
#for m in client.models.list():
#    print(m.name)


MODELS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.1-flash-lite"]  # first choice, then backup
RETRIES_PER_MODEL = 3
today = date.today()

config = types.GenerateContentConfig(
    system_instruction=(
        f"You are a hotel booking assistant for a Turkish travel agency. "
        f"Use search_hotels to find hotels and get_hotel_details for questions about a specific hotel. "
        f"Only recommend hotels returned by the tools, and never invent prices or availability. "
        f"To book, use create_booking only after the customer has chosen a room and confirmed "
        f"the hotel, dates, guests and total price. "
        f"Refer to rooms by hotel name, room type and meal plan in plain words (e.g. 'breakfast included'). "
        f"Never show room_id, hotel_id or board codes like BB or HB to the customer. "
        f"Today is {today.strftime('%A, %Y-%m-%d')}"
    ),
    tools=[search_hotels, get_hotel_details, create_booking], automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


def send_with_fallback(chat, current_model, message):
    """Send a message, retrying on server errors and falling back to the next model.

    Returns (chat, current_model, response), because the chat and model
    may change if a fallback happened.
    """
    for model in MODELS[MODELS.index(current_model):]:
        if model != current_model:
            print(f"Switching to {model}...")
            chat = client.chats.create(model=model, config=config,
                                       history=chat.get_history())
            current_model = model

        for attempt in range(RETRIES_PER_MODEL):
            try:
                response = chat.send_message(message)
                return chat, current_model, response
            except errors.ServerError:
                wait = 2 ** attempt  # 1s, 2s, 4s
                print(f"{model} unavailable (attempt {attempt + 1}/{RETRIES_PER_MODEL}), "
                      f"retrying in {wait}s...")
                time.sleep(wait)

    raise RuntimeError("All models are unavailable right now. Try again later.")


TOOLS = {"search_hotels": search_hotels, "get_hotel_details": get_hotel_details, "create_booking": create_booking}
NEEDS_APPROVAL = {"create_booking"}
MAX_TOOL_ROUNDS = 5

# manuel tool calling-agent ilk adım llm i nasıl çağıracağını yönetiyor
def run_turn(chat, current_model, user_input):
    """Handle one user message, running any tool calls the model asks for.

    Returns (chat, current_model, response) like send_with_fallback.
    """
    chat, current_model, response = send_with_fallback(chat, current_model, user_input)

    for _ in range(MAX_TOOL_ROUNDS):
        if not response.function_calls:
            return chat, current_model, response

        parts = []
        for call in response.function_calls:
            print(f"[tool] {call.name}({call.args})")
            func = TOOLS.get(call.name)
            if func is None:
                result = {"error": f"Unknown tool: {call.name}"}

            elif call.name in NEEDS_APPROVAL and input("Confirm booking? (y/n)").strip().lower() not in ("y", "yes"):
                result = {"error": "The user declined this booking. Nothing was booked. "
                                   "Ask the user what they would like to change."}
            else:
                try:
                    result = func(**call.args)
                except TypeError as e:  # model passed bad/missing arguments
                    result = {"error": str(e)}
            parts.append(types.Part.from_function_response(
                name=call.name, response={"result": result}))

        chat, current_model, response = send_with_fallback(chat, current_model, parts)

    raise RuntimeError(f"Stopped after {MAX_TOOL_ROUNDS} tool rounds.")



def main():
    current_model = MODELS[0]
    chat = client.chats.create(model=current_model, config=config)

    print("Hotel assistant ready. Type 'quit' to exit.")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "quit":
            break

        try:
            chat, current_model, response = run_turn(chat, current_model, user_input)
        except RuntimeError as e:
            print(e)
            continue

        print("Agent:", response.text)

        # debug: show the hidden tool loop (remove later)
        for step in response.automatic_function_calling_history or []:
            for part in step.parts:
                if part.function_call:
                    print(f"  [tool call] {part.function_call.name}({dict(part.function_call.args)})")


if __name__ == "__main__":
    main()
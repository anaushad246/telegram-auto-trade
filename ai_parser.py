import json
import google.generativeai as genai
import config

# --- Configure the Gemini Client ---
genai.configure(api_key=config.GEMINI_API_KEY)

# --- Set up the model ---
json_generation_config = genai.GenerationConfig(
    response_mime_type="application/json"
)
model = genai.GenerativeModel(
    'models/gemini-flash-latest', # This is the model name that works for you
    generation_config=json_generation_config
)

# --- THIS IS THE UPGRADED PROMPT ---
SYSTEM_PROMPT = """
You are an expert trading assistant. Your task is to parse raw text from Telegram signals
and convert them into a structured JSON object.

RULES:
1.  **Symbols:** Convert common names to standard MT5 symbols (e.g., "Gold" or "XAU" -> "XAUUSD", "GBP" -> "GBPUSD").
2.  **Action:** Must be "BUY" or "SELL".
3.  **Order Type:**
    - If the signal says "buy now", "sell now", or just gives an entry range, it is "MARKET".
    - If the signal explicitly says "BUY LIMIT", "SELL LIMIT", "BUY STOP", or "SELL STOP", you MUST use that exact type (e.g., "BUY_LIMIT").
4.  **Entry Price:**
    - For "MARKET" orders, this is the "safe" entry zone. It can be a range (e.g., [4001.0, 3999.0]) or a single price (e.g., [4000.5]).
    - For **Pending Orders** (LIMIT/STOP), this is the *trigger price*. It will always be a single price (e.g., [3990.0]).
    - If no entry is given, set to null.
5.  **Stop Loss (SL):** Must be a single float.
6.  **Take Profits (TP):** Must be a list of floats. Extract all TPs.
7.  **Not a Signal:** If the text is a chat message, news, or anything other than a trade signal, return `null`.

JSON FORMAT EXAMPLES:

Example 1 (Market Order with range):
{
  "symbol": "XAUUSD", "action": "SELL", "order_type": "MARKET",
  "entry_range": [4001.0, 3999.0],
  "stop_loss": 4004.0, "take_profits": [3995.0, 3990.0]
}

Example 2 (Market Order with single price):
{
  "symbol": "XAUUSD", "action": "SELL", "order_type": "MARKET",
  "entry_range": [4000.5],
  "stop_loss": 4005.0, "take_profits": [3998.0, 3996.0]
}

Example 3 (Pending Order):
{
  "symbol": "XAUUSD", "action": "BUY", "order_type": "BUY_LIMIT",
  "entry_range": [3990.0],
  "stop_loss": 3985.0, "take_profits": [4000.0]
}
"""

def parse_signal_with_ai(raw_text):
    """
    Uses Gemini to parse raw signal text into a structured JSON.
    """
    print(f"🧠 [Gemini Parser] Analyzing text: \"{raw_text[:50]}...\"")
    try:
        full_prompt = SYSTEM_PROMPT + "\n\n--- PARSE THIS SIGNAL --- \n" + raw_text

        response = model.generate_content(full_prompt)
        
        result_json = response.text
        
        if result_json == "null":
            print("🧠 [Gemini Parser] Message is not a trade signal.")
            return None
            
        signal_data = json.loads(result_json)
        
        if not all(k in signal_data for k in ["symbol", "action", "order_type", "stop_loss", "take_profits"]):
             print(f"❌ [Gemini Parser] AI output missing required fields: {result_json}")
             return None

        print(f"✅ [Gemini Parser] Signal parsed successfully: {signal_data}")
        return signal_data

    except Exception as e:
        print(f"❌ [Gemini Parser] Error: {e}")
        return None
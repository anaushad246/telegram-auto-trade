import json
import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)
json_generation_config = genai.GenerationConfig(response_mime_type="application/json")
model = genai.GenerativeModel('models/gemini-flash-latest', generation_config=json_generation_config)

# --- THIS IS THE FINAL UPGRADED PROMPT ---
SYSTEM_PROMPT = """
You are an expert trading assistant. Your task is to parse raw text from Telegram signals
and convert them into a structured JSON object.

RULES:
1.  **Symbols:** Convert common names to standard MT5 symbols (e.g., "Gold" or "XAU" -> "XAUUSD").
2.  **Action:**
    - "BUY" or "SELL" for new trades.
    - "MODIFY" for changing existing trades.
3.  **Order Type:**
    - New Trades: "MARKET", "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP".
    - Modify Trades:
        - "BE", "Break Even", "SL to Entry" -> "BREAK_EVEN"
        - "Move SL", "SL Trail", "Update SL" -> "MOVE_SL"
        - "Move TP", "TP Reset", "Update TP" -> "MOVE_TP"
4.  **Entry Price (entry_range):**
    - "MARKET" orders: A range [4001.0, 3999.0] or a single price [4000.5].
    - "Pending Orders": The trigger price [3990.0].
    - "MODIFY" actions: null.
5.  **Stop Loss (sl) & Take Profits (tp_list):**
    - For new trades, extract these.
    - For "MODIFY" actions, these can be null.
6.  **Value (value):**
    - For "MOVE_SL" or "MOVE_TP", this is the new target price. (e.g., "Move SL XAUUSD 4010" -> "value": 4010.0)
    - For "BREAK_EVEN" or new trades, this is null.
7.  **Not a Signal:** If the text is a chat message, news, or anything other than a trade signal, return `null`.

JSON FORMAT EXAMPLES:

Example 1 (Market Order):
{
  "symbol": "XAUUSD", "action": "SELL", "order_type": "MARKET",
  "entry_range": [4001.0, 3999.0], "sl": 4004.0, "tp_list": [3995.0, 3990.0], "value": null
}

Example 2 (Pending Order):
{
  "symbol": "XAUUSD", "action": "BUY", "order_type": "BUY_LIMIT",
  "entry_range": [3990.0], "sl": 3985.0, "tp_list": [4000.0], "value": null
}

Example 3 (Manual Break-Even Signal):
{
  "symbol": "XAUUSD", "action": "MODIFY", "order_type": "BREAK_EVEN",
  "entry_range": null, "sl": null, "tp_list": null, "value": null
}

Example 4 (Manual SL Trail Signal):
{
  "symbol": "XAUUSD", "action": "MODIFY", "order_type": "MOVE_SL",
  "entry_range": null, "sl": null, "tp_list": null, "value": 4010.0
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
        
        if not all(k in signal_data for k in ["symbol", "action", "order_type"]):
             print(f"❌ [Gemini Parser] AI output missing required fields: {result_json}")
             return None

        print(f"✅ [Gemini Parser] Signal parsed successfully: {signal_data}")
        return signal_data

    except Exception as e:
        print(f"❌ [Gemini Parser] Error: {e}")
        return None
import json
import google.generativeai as genai
# import config
from . import config

# ==========================================
#   INITIALIZE GEMINI
# ==========================================
try:
    genai.configure(api_key=config.GEMINI_API_KEY)

    # Force JSON output from Gemini
    json_generation_config = genai.GenerationConfig(
        response_mime_type="application/json"
    )

    # Use the correct model for OLD API (v1beta)
    model = genai.GenerativeModel(
        model_name="models/gemini-flash-latest",
        generation_config=json_generation_config
    )

    print("✅ [Gemini Parser] Model initialized: models/gemini-flash-latest")

except Exception as e:
    print(f"❌ [Gemini Parser] Failed to initialize Gemini model: {e}")
    model = None


# ==========================================
SYSTEM_PROMPT = """
You are an expert trading assistant. Your job is to convert Telegram signal text
into a strict JSON object used for trading automation.

STRICT RULES:

1. SYMBOL:
   - "Gold", "GOLD", "XAU", "XAUUSD" → "XAUUSD"
   - If symbol cannot be detected → return null.

2. ACTION:
   - BUY or SELL for new trades.
   - MODIFY for updates.
   - If action cannot be detected → return null.

3. ORDER TYPE:
   - MARKET, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP.
   - For modify actions: BREAK_EVEN, MOVE_SL, MOVE_TP.
   - If order type cannot be detected → return null.

4. ENTRY RANGE:
   - MARKET: include 1 or 2 numbers (entry zone).
   - Pending orders: include 1 number (trigger price).
   - MODIFY: entry_range = null.

5. STOP LOSS (sl):
   - REQUIRED for all new trades.
   - Must be a single number.
   - If no valid SL detected → return null.

6. TAKE PROFIT LIST (tp_list):
   - REQUIRED for all new trades.
   - Must contain at least ONE valid numeric TP.
   - If no TP detected → return null.

7. MODIFY ACTIONS:
   - For MOVE_SL or MOVE_TP → include "value" as the updated level.
   - For BREAK_EVEN → value = null.
   - For MODIFY actions sl=null, tp_list=null.

8. If the message is NOT a valid trading signal → return null.

9. Always respond in VALID JSON ONLY:
{
  "symbol": "",
  "action": "",
  "order_type": "",
  "entry_range": [],
  "sl": 0,
  "tp_list": [],
  "value": null
}

NO explanations, NO text — only JSON or null.
"""

# ==========================================
#   PARSER FUNCTION
# ==========================================
def parse_signal_with_ai(raw_text):
    """
    Uses Gemini to parse raw signal text into a structured JSON object.
    """

    if not model:
        print("❌ [Gemini Parser] Model not initialized.")
        return None

    print(f"🧠 [Gemini Parser] Analyzing: \"{raw_text[:60]}...\"")

    try:
        full_prompt = SYSTEM_PROMPT + "\n\n--- PARSE THIS SIGNAL ---\n" + raw_text

        # Make request to Gemini
        response = model.generate_content(full_prompt)

        if not response:
            print("❌ [Gemini Parser] Empty response from Gemini.")
            return None

        result_json = response.text

        # Clean markdown if included
        if result_json.startswith("```"):
            result_json = (
                result_json.replace("```json", "")
                .replace("```", "")
                .strip()
            )

        if result_json == "null":
            print("ℹ [Gemini Parser] Not a valid trading signal.")
            return None

        # Convert to Python dict
        signal_data = json.loads(result_json)

        # Validate required fields
        required = ["symbol", "action", "order_type"]
        if not all(k in signal_data for k in required):
            print("❌ [Gemini Parser] Missing required fields:", signal_data)
            return None

        print("✅ [Gemini Parser] Parsed:", signal_data)
        return signal_data

    except Exception as e:
        print(f"❌ [Gemini Parser] Parsing Error: {e}")
        return None

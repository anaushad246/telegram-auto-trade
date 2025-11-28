import json
import google.generativeai as genai
from app.config import config
from app.log_setup import setup_logger
from app.models.signal import TradeSignal

logger = setup_logger("AIService")

class AIService:
    def __init__(self):
        try:
            genai.configure(api_key=config.GEMINI_API_KEY)
            
            # Force JSON output from Gemini
            json_generation_config = genai.GenerationConfig(
                response_mime_type="application/json"
            )

            # Use the correct model for OLD API (v1beta)
            self.model = genai.GenerativeModel(
                model_name="models/gemini-flash-latest",
                generation_config=json_generation_config
            )
            logger.info("Model initialized: models/gemini-flash-latest")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

        self.system_prompt = """
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

    async def parse_signal(self, raw_text: str) -> Optional[TradeSignal]:
        """
        Uses Gemini to parse raw signal text into a structured TradeSignal object.
        """
        if not self.model:
            logger.error("Model not initialized.")
            return None

        logger.info(f"Analyzing: \"{raw_text[:60]}...\"")

        try:
            full_prompt = self.system_prompt + "\n\n--- PARSE THIS SIGNAL ---\n" + raw_text

            # Make request to Gemini (synchronous call wrapped if needed, but genai is sync by default usually unless async method used)
            # The library supports async but standard generate_content is sync. 
            # For high throughput we might want to run in executor, but for now direct call is fine or use async_generate_content if available.
            # checking docs: generate_content_async exists.
            
            response = await self.model.generate_content_async(full_prompt)

            if not response:
                logger.error("Empty response from Gemini.")
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
                logger.info("Not a valid trading signal.")
                return None

            # Convert to Python dict
            signal_data = json.loads(result_json)

            # Validate with Pydantic
            try:
                signal = TradeSignal(**signal_data)
                logger.info(f"Parsed: {signal}")
                return signal
            except Exception as validation_error:
                logger.error(f"Validation Error: {validation_error} | Data: {signal_data}")
                return None

        except Exception as e:
            logger.error(f"Parsing Error: {e}")
            return None

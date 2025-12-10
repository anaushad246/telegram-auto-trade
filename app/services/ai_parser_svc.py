import json
from typing import Optional
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
                model_name="models/gemini-2.5-flash-lite",
                generation_config=json_generation_config
            )
            logger.info("Model initialized: models/gemini-2.5-flash-lite")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            self.model = None

        self.system_prompt = """
You are a trading-signal parser. Convert the given message into the following JSON:

{
  "symbol": "",
  "action": "",
  "order_type": "",
  "entry_range": [],
  "sl": 0,
  "tp_list": [],
  "value": null
}

Rules:
1. SYMBOL: Map "Gold", "GOLD", "XAU", "XAUUSD" -> "XAUUSD". If missing -> null.
2. ACTION: BUY, SELL, or MODIFY. If missing -> null.
3. ORDER TYPE:
   - New orders: MARKET, BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP.
   - Modify: BREAK_EVEN, MOVE_SL, MOVE_TP.
4. ENTRY RANGE:
   - MARKET: 1-2 numbers.
   - Pending: 1 number.
   - MODIFY: null.
5. SL: Required for new trades. One number. If missing -> null.
6. TP_LIST: At least 1 TP. If none -> null.
7. MODIFY:
   - MOVE_SL or MOVE_TP -> "value" = updated level.
   - BREAK_EVEN -> value = null.
   - For MODIFY: sl = null, tp_list = null.
8. If not a valid trading signal -> return null.
9. Output JSON only. No text.

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

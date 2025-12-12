import json
from typing import Optional
# import google.generativeai as genai # REMOVE THIS LINE
import openai # ADD THIS LINE
from app.config import config
from app.log_setup import setup_logger
from app.models.signal import TradeSignal

logger = setup_logger("AIService")

class AIService:
    def __init__(self):
        try:
            # Configure the OpenAI client to use the OpenRouter API endpoint
            self.client = openai.AsyncClient(
                base_url="https://openrouter.ai/api/v1", # OpenRouter Base URL
                api_key=config.OPENROUTER_API_KEY
            )
            # The model name is now retrieved from config
            self.model_name = config.OPENROUTER_MODEL
            
            logger.info(f"AI Service initialized. Using model: {self.model_name} via OpenRouter.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter client: {e}")
            self.client = None
            self.model_name = None

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
        Uses OpenRouter/DeepSeek to parse raw signal text into a structured TradeSignal object.
        """
        if not self.client:
            logger.error("AI client not initialized.")
            return None

        logger.info(f"Analyzing: \"{raw_text[:60]}...\" using {self.model_name}")

        try:
            # OpenRouter uses the standard Chat Completions API format
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": raw_text}
            ]

            # Use the chat completions endpoint, requesting JSON output
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            if not response.choices:
                logger.error("Empty response from OpenRouter.")
                return None

            result_json = response.choices[0].message.content
            
            # Clean markdown if included (models sometimes ignore the JSON format request)
            if result_json.startswith("```"):
                result_json = (
                    result_json.replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

            # Check for null signal responses
            if result_json.lower() == "null" or not result_json:
                logger.info("Not a valid trading signal.")
                return None

            # Convert to Python dict
            signal_data = json.loads(result_json)
            
            # Unwrap if the model wraps the JSON in a top-level key (e.g., {"signal": {...}})
            if isinstance(signal_data, dict) and 'signal' in signal_data and signal_data.keys() == {'signal'}:
                signal_data = signal_data['signal']
# ... inside parse_signal method ...

            # Validate with Pydantic
            try:
                signal = TradeSignal(**signal_data)
                logger.info(f"Parsed: {signal}")
                return signal
            except Exception:
                # CHANGED: Don't print huge errors for chatter. Just log a simple warning.
                logger.warning(f"Ignored message: AI parsed data but it was incomplete (likely not a signal).")
                return None

        except Exception as e:
            logger.error(f"Parsing Error: {e}")
            return None
        #     # Validate with Pydantic
        #     try:
        #         signal = TradeSignal(**signal_data)
        #         logger.info(f"Parsed: {signal}")
        #         return signal
        #     except Exception as validation_error:
        #         logger.error(f"Validation Error: {validation_error} | Data: {signal_data}")
        #         return None

        # except Exception as e:
        #     logger.error(f"Parsing Error: {e}")
        #     return None
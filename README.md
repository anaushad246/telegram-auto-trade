# Telegram to MT5 AI Bot

This bot uses AI to parse signals from Telegram groups and automatically execute trades on MetaTrader 5.

## Setup

1.  **Clone the project:**
    ```bash
    git clone <your-repo-url>
    cd telegram-mt5-bot
    ```

2.  **Create your .env file:**
    -   Copy `example.env` (if you have one) or create `.env` from scratch.
    -   Fill in all your credentials (Telegram, MT5, OpenAI).
    -   Add your target Telegram group names to `GROUP_NAMES`, separated by commas.

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Bot

1.  **Run the main file:**
    ```bash
    python main.py
    ```

2.  The first time you run it, Telethon will ask you to log in. You will need to enter your phone number (`PHONE` from `.env`) and the code Telegram sends you.

3.  Once logged in, it will create a `.session` file and log in automatically next time. The bot is now live and waiting for signals.

#system prompts: You are an expert trading assistant. Your job is to convert Telegram signal text
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
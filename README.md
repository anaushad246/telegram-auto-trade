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
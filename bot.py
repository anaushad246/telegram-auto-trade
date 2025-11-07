# import os
# from telethon import TelegramClient, events
# import MetaTrader5 as mt5
# from dotenv import load_dotenv
# import re

# # Load environment variables
# load_dotenv()

# API_ID = int(os.getenv("API_ID"))
# API_HASH = os.getenv("API_HASH")
# PHONE = os.getenv("PHONE")
# GROUP_NAME = os.getenv("GROUP_NAME")

# MT5_LOGIN = int(os.getenv("MT5_LOGIN"))
# MT5_PASSWORD = os.getenv("MT5_PASSWORD")
# MT5_SERVER = os.getenv("MT5_SERVER")

# # Initialize Telegram client
# client = TelegramClient('session', API_ID, API_HASH)

# # Initialize MetaTrader
# if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
#     print("❌ MT5 initialization failed:", mt5.last_error())
# else:
#     print("✅ Connected to MT5")

# def parse_signal(text):
#     """
#     Expected message format:
#     BUY EURUSD
#     Entry: 1.0850
#     SL: 1.0830
#     TP: 1.0900
#     """
#     side = "BUY" if "BUY" in text.upper() else "SELL"
#     pair = re.search(r"(EURUSD|GBPUSD|USDJPY|XAUUSD|[A-Z]{6})", text.upper())
#     entry = re.search(r"Entry[:\-]?\s*([\d.]+)", text)
#     sl = re.search(r"SL[:\-]?\s*([\d.]+)", text)
#     tp = re.search(r"TP[:\-]?\s*([\d.]+)", text)
#     if pair and entry and sl and tp:
#         return {
#             "symbol": pair.group(1),
#             "side": side,
#             "entry": float(entry.group(1)),
#             "sl": float(sl.group(1)),
#             "tp": float(tp.group(1))
#         }
#     return None

# def place_trade(signal):
#     symbol = signal["symbol"]
#     side = signal["side"]
#     sl = signal["sl"]
#     tp = signal["tp"]
#     lot = 0.1

#     price = mt5.symbol_info_tick(symbol).ask if side == "BUY" else mt5.symbol_info_tick(symbol).bid
#     order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

#     trade_request = {
#         "action": mt5.TRADE_ACTION_DEAL,
#         "symbol": symbol,
#         "volume": lot,
#         "type": order_type,
#         "price": price,
#         "sl": sl,
#         "tp": tp,
#         "deviation": 20,
#         "magic": 123456,
#         "comment": "Telegram Auto Trade"
#     }

#     result = mt5.order_send(trade_request)
#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         print("❌ Trade failed:", result)
#     else:
#         print(f"✅ {side} {symbol} executed at {price}")

# @client.on(events.NewMessage(chats=GROUP_NAME))
# async def signal_handler(event):
#     text = event.raw_text
#     signal = parse_signal(text)
#     if signal:
#         print("📩 Signal received:", signal)
#         place_trade(signal)

# print("🚀 Bot started... waiting for signals...")
# client.start(phone=PHONE)
# client.run_until_disconnected()


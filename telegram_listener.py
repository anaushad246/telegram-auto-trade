from telethon import TelegramClient, events
import config
import ai_parser
import trade_manager

# --- THIS IS THE FIX ---
# Your selected list of 3 group IDs:
CHAT_IDS = [
    -1002141832713,  # 'GOLDHILL CAPITAL FX/CRYPTO TRADING HUB'
    -1002192816520,  # 'Alphabet Free'
    -1001774783341,   # 'GARY GOLD TRADER'
    -1002130822880,   # 'YoForex Gold'
    -1002416814232,   # 'Easy♛'
    -1001538406132,  # 'Elevating Forex | GijsFX'
    -1001251070444,  # 'HUGO TRADER™'
    -1001313672961,  # 'Gold Snipers'
    -1001758700941,  # 'Forexero - Forex Signals'
    -1003292339571,  # 'Test Group'
]
# --- END FIX ---


client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

async def signal_handler(event):
    """
    This function is called whenever a new message arrives
    in the groups we are listening to.
    """
    message_text = event.raw_text
    
    # We no longer need the title, we have the ID
    print(f"\n📩 [Telegram] New Message from chat ID: {event.chat_id}")
    
    try:
        # 1. Send the raw text to the AI parser
        signal_json = ai_parser.parse_signal_with_ai(message_text)
        
        # 2. If the AI returns a valid signal, execute the trade
        if signal_json:
            trade_manager.execute_trade_from_json(signal_json)
        
    except Exception as e:
        print(f"❌ [Handler] Error processing message: {e}")

def start_listening():
    """
    Starts the Telethon client and listens for messages.
    """
    print("🎧 [Telegram] Bot is starting...")
    
    with client:
        # --- We now use the CHAT_IDS list ---
        @client.on(events.NewMessage(chats=CHAT_IDS))
        async def handler(event):
            await signal_handler(event)
            
        print(f"✅ [Telegram] Listening for messages in: {len(CHAT_IDS)} groups (by ID)")
        print("🚀 Bot is now running. Waiting for signals...")
        
        # This keeps the bot running indefinitely
        client.run_until_disconnected()
# from telethon import TelegramClient, events
# import config

# client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

# @client.on(events.NewMessage(incoming=True))
# async def id_finder_handler(event):
#     """
#     This handler listens to EVERY message you receive
#     and prints the sender's name and ID.
#     """
#     try:
#         # Get the chat title and ID
#         chat_title = event.chat.title
#         chat_id = event.chat_id
        
#         # Print it to your terminal
#         print(f"✅ Message from: '{chat_title}' (ID: {chat_id})")
        
#     except Exception as e:
#         # This will happen for private messages, just ignore them
#         pass

# def start_listening():
#     print("===================================")
#     print("   🤖 ID FINDER MODE IS ON 🤖   ")
#     print("===================================")
#     print("1. Go to your Telegram app.")
#     print("2. Post 'hello' in EACH of your signal groups.")
#     print("3. Copy the (ID: ...) number from here.")
#     print("4. Press Ctrl+C when you are done.")
#     print("===================================")
    
#     with client:
#         client.run_until_disconnected()
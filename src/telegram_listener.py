from telethon import TelegramClient, events
from . import config
from . import ai_parser
from . import trade_manager
import asyncio # New import

# --- THIS IS THE GROUP-TO-MAGIC NUMBER MAP ---
# This is the "stamp" that tracks which group a trade belongs to.
# You MUST add all your group IDs and give them a unique number
CHAT_ID_TO_MAGIC_MAP = {
     -1002141832713: 1001,  # 'GOLDHILL CAPITAL FX/CRYPTO TRADING HUB' 1
    -1002192816520: 1002,  # 'Alphabet Free'
    -1001774783341: 1003,  # 'GARY GOLD TRADER'
    -1002130822880: 1004,  # 'YoForex Gold'
    -1002416814232: 1005,  # 'Easy♛'
    -1001538406132: 1006,  # 'Elevating Forex | GijsFX'
    -1001251070444: 1007,  # 'HUGO TRADER™'
    -1001313672961: 1008,  # 'Gold Snipers'
    -1001758700941: 1009,  # 'Forexero - Forex Signals'
    -1003292339571: 1010   # 'Test Group'
}
# --- END MAP ---


client = TelegramClient('bot_session', config.API_ID, config.API_HASH)

async def signal_handler(event):
    """
    This function is called whenever a new message arrives
    in the groups we are listening to.
    """
    message_text = event.raw_text
    chat_id = event.chat_id
    
    print(f"\n📩 [Telegram] New Message from chat ID: {chat_id}")
    
    # --- MAGIC NUMBER LOOKUP ---
    # Find the magic number for the group that sent the message
    magic_number = CHAT_ID_TO_MAGIC_MAP.get(chat_id)
    if not magic_number:
        print(f"⚠️ [Listener] SKIPPED: Message from unknown group ID {chat_id}. Add it to the map.")
        return
    # --- END LOOKUP ---

    try:
        # 1. Send the raw text to the AI parser
        signal_json = ai_parser.parse_signal_with_ai(message_text)
        
        # 2. If the AI returns a valid signal, execute the trade
        if signal_json:
            # Pass BOTH the signal and the group's magic number to the trader
            trade_manager.execute_trade_from_json(signal_json, magic_number)
        
    except Exception as e:
        print(f"❌ [Handler] Error processing message: {e}")

async def start_listening():
    """
    Starts the Telethon client and registers the handler.
    This function will be run by main.py.
    """
    print("🎧 [Telegram] Bot is starting...")
    
    # Get the list of IDs from our map
    chat_ids_to_listen = list(CHAT_ID_TO_MAGIC_MAP.keys())
    
    @client.on(events.NewMessage(chats=chat_ids_to_listen))
    async def handler(event):
        await signal_handler(event)
        
    print(f"✅ [Telegram] Listening for messages in: {len(chat_ids_to_listen)} groups (by ID)")
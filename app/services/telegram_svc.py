from telethon import TelegramClient, events
from app.config import config
from app.log_setup import setup_logger
from typing import Callable, Awaitable

logger = setup_logger("TelegramService")

# Map logic moved here or kept in config. 
# For now, let's keep it here as it's specific to the listener logic mapping chat IDs to magic numbers.
CHAT_ID_TO_MAGIC_MAP = {
     -1002141832713: 1001,  # 'GOLDHILL CAPITAL FX/CRYPTO TRADING HUB'
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

class TelegramBot:
    def __init__(self, callback: Callable[[str, int], Awaitable[None]]):
        self.client = TelegramClient('bot_session', config.API_ID, config.API_HASH)
        self.callback = callback

    async def start(self):
        logger.info("Bot is starting...")
        
        # Get the list of IDs from our map
        chat_ids_to_listen = list(CHAT_ID_TO_MAGIC_MAP.keys())
        
        @self.client.on(events.NewMessage(chats=chat_ids_to_listen))
        async def handler(event):
            await self._signal_handler(event)
            
        logger.info(f"Listening for messages in: {len(chat_ids_to_listen)} groups (by ID)")
        await self.client.start(phone=config.PHONE)
        await self.client.run_until_disconnected()

    async def _signal_handler(self, event):
        message_text = event.raw_text
        chat_id = event.chat_id
        
        logger.info(f"New Message from chat ID: {chat_id}")
        
        magic_number = CHAT_ID_TO_MAGIC_MAP.get(chat_id)
        if not magic_number:
            logger.warning(f"SKIPPED: Message from unknown group ID {chat_id}.")
            return

        try:
            # Invoke the callback (pipeline)
            await self.callback(message_text, magic_number)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

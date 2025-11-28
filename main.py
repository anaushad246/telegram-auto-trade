import asyncio
import sys
from app.config import config
from app.log_setup import setup_logger
from app.services.telegram_svc import TelegramBot
from app.services.ai_parser_svc import AIService
from app.services.mt5_svc import MT5Service
from app.services.trade_executor import TradeExecutor
from app.workers.monitor import MonitorWorker

logger = setup_logger("Main")

async def main():
    logger.info("Starting Forex Auto-Trading Bot (SOA)...")

    # 1. Initialize Services
    ai_service = AIService()
    mt5_service = MT5Service()
    
    # Connect to MT5 immediately
    if not mt5_service.connect():
        logger.critical("Failed to connect to MT5. Exiting.")
        return

    trade_executor = TradeExecutor(mt5_service)
    monitor_worker = MonitorWorker(trade_executor)
    
    # 2. Define the pipeline (Orchestration)
    async def pipeline(text: str, magic_number: int):
        """
        Callback function triggered by new Telegram messages.
        """
        logger.info(f"Pipeline triggered for group {magic_number}")
        
        # A. Parse with AI
        signal = await ai_service.parse_signal(text)
        
        # B. Execute if valid
        if signal:
            # We run this synchronously (blocking the event loop slightly) or offload it.
            # Since MT5 python library is blocking, we might want to run it in an executor if high volume.
            # For now, direct call is fine as per original design.
            trade_executor.execute_signal(signal, magic_number)

    # 3. Initialize Telegram Bot with the pipeline callback
    bot = TelegramBot(callback=pipeline)
    
    # 4. Run everything
    try:
        await asyncio.gather(
            bot.start(),
            monitor_worker.start_loop()
        )
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
    finally:
        mt5_service.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
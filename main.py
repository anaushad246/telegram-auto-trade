import sys
import asyncio
from src import telegram_listener
from src import trade_manager
from src import config

async def monitor_loop():
    """
    Runs the automatic BE monitor every 10 seconds.
    """
    while True:
        try:
            trade_manager.monitor_automatic_be()
        except Exception as e:
            print(f"❌ [Monitor Loop] Error: {e}")
        
        await asyncio.sleep(10) # Wait 10 seconds

async def main():
    """
    Main entry point for the bot.
    Connects to MT5, starts the trade monitor, and starts the Telegram listener.
    """
    print("================================")
    print("   Telegram to MT5 AI Bot (v2)  ")
    print("================================")
    
    try:
        # 1. Connect to MetaTrader 5
        if not trade_manager.connect_to_mt5():
            print("Failed to connect to MT5. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        # 2. Start the Telegram listener (does not block)
        await telegram_listener.client.start(phone=config.PHONE)
        await telegram_listener.start_listening()
        
        # 3. Start the new Auto-BE Monitor in the background
        print("💡 [Monitor] Automatic BE monitor is starting...")
        monitor_task = asyncio.create_task(monitor_loop())
        
        # 4. Run forever
        print("🚀 Bot is now fully running. Waiting for signals and monitoring trades...")
        await telegram_listener.client.run_until_disconnected()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down (Ctrl+C detected)...")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        # 5. Always shut down the MT5 connection gracefully
        trade_manager.shutdown_mt5()
        print("✅ Bot has been shut down.")

if __name__ == "__main__":
    asyncio.run(main())
# --- NEW CODE FOR main.py ---
import sys
import telegram_listener  # Changed
import trade_manager      # Changed
import config             # Changed

def main():
    """
    Main entry point for the bot.
    Connects to MT5 and starts the Telegram listener.
    """
    print("================================")
    print("   Telegram to MT5 AI Bot   ")
    print("================================")
    
    try:
        # 1. Connect to MetaTrader 5
        if not trade_manager.connect_to_mt5():
            print("Failed to connect to MT5. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        # 2. Start the Telegram listener
        # This function will run forever until you stop it (Ctrl+C)
        telegram_listener.start_listening()
        
    except KeyboardInterrupt:
        print("\n🛑 Bot shutting down (Ctrl+C detected)...")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        # 3. Always shut down the MT5 connection gracefully
        trade_manager.shutdown_mt5()
        print("✅ Bot has been shut down.")

if __name__ == "__main__":
    main()
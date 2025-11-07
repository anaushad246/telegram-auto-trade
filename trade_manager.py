import MetaTrader5 as mt5
import config
import time

def connect_to_mt5():
    """
    Connects and logs in to the MetaTrader 5 terminal.
    """
    print("📈 [MT5] Connecting...")
    if not mt5.initialize(
        login=config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER
    ):
        print(f"❌ [MT5] Initialization failed: {mt5.last_error()}")
        return False
    
    print(f"✅ [MT5] Connected to {config.MT5_SERVER} as {config.MT5_LOGIN}.")
    return True

def shutdown_mt5():
    """
    Shuts down the connection to MetaTrader 5.
    """
    print("📈 [MT5] Shutting down connection...")
    mt5.shutdown()

def execute_trade_from_json(signal):
    """
    Executes trades based on the parsed signal JSON from the AI.
    Handles both MARKET and PENDING orders.
    """
    try:
        # --- 1. Get Base Signal Data ---
        symbol = signal["symbol"]
        action = signal["action"] # "BUY" or "SELL"
        order_type_str = signal["order_type"] # "MARKET", "BUY_LIMIT", etc.
        entry_range = signal.get("entry_range")
        sl = signal["stop_loss"]
        tp_list = signal["take_profits"]
        lot_size = config.FIXED_LOT_SIZE

        # --- 2. Prepare Symbol ---
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            print(f"❌ [Trader] Symbol {symbol} not found in MT5.")
            return
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
            time.sleep(1) 

        # --- 3. LOGIC FOR MARKET ORDERS ---
        if order_type_str == "MARKET":
            print("📈 [Trader] Processing MARKET order.")
            
            # Get current price
            if action == "BUY":
                price = mt5.symbol_info_tick(symbol).ask
            else: # SELL
                price = mt5.symbol_info_tick(symbol).bid

            # Price Safety Check
            if entry_range:
                if len(entry_range) == 2: # Range check
                    min_entry = min(entry_range)
                    max_entry = max(entry_range)
                    if not (min_entry <= price <= max_entry):
                        print(f"⚠️ [Trader] SKIPPED: Current price {price} is outside entry range {min_entry}-{max_entry}.")
                        return
                    print(f"✅ [Trader] Price check passed (range): {price} is within {min_entry}-{max_entry}.")
                
                elif len(entry_range) == 1: # Single price check
                    target_price = entry_range[0]
                    if action == "BUY" and price > target_price:
                        print(f"⚠️ [Trader] SKIPPED: Current price {price} is worse than target entry {target_price}.")
                        return
                    elif action == "SELL" and price < target_price:
                        print(f"⚠️ [Trader] SKIPPED: Current price {price} is worse than target entry {target_price}.")
                        return
                    print(f"✅ [Trader] Price check passed (single): {price} is at or better than target {target_price}.")

            # Execute Market Order(s)
            print(f"📈 [Trader] Placing {len(tp_list)} MARKET trades for {action} {symbol} @ {price}...")
            for tp in tp_list:
                trade_request = {
                    "action": mt5.TRADE_ACTION_DEAL, # Market Order
                    "symbol": symbol,
                    "volume": lot_size,
                    "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
                    "price": price,
                    "sl": float(sl),
                    "tp": float(tp),
                    "deviation": 20,
                    "magic": 123456,
                    "comment": "Telegram AI Bot (Market)",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK,
                }
                result = mt5.order_send(trade_request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print(f"❌ [Trader] Market Trade FAILED for TP {tp}. Code: {result.retcode}, Comment: {result.comment}")
                else:
                    print(f"✅ [Trader] Market Trade PLACED for TP {tp}. Order: {result.order}")

        # --- 4. LOGIC FOR PENDING ORDERS ---
        elif order_type_str in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"]:
            print("📈 [Trader] Processing PENDING order.")

            # Map AI string to MT5 constant
            order_type_map = {
                "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
                "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
                "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
                "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP
            }
            mt5_order_type = order_type_map[order_type_str]

            # For pending orders, the entry_range is just the trigger price
            if not entry_range or len(entry_range) != 1:
                print(f"❌ [Trader] SKIPPED: Pending order signal is missing its trigger price.")
                return
            
            trigger_price = entry_range[0]

            # Execute Pending Order(s)
            print(f"📈 [Trader] Placing {len(tp_list)} PENDING trades for {action} {symbol} @ {trigger_price}...")
            for tp in tp_list:
                trade_request = {
                    "action": mt5.TRADE_ACTION_PENDING, # Pending Order
                    "symbol": symbol,
                    "volume": lot_size,
                    "type": mt5_order_type,
                    "price": float(trigger_price), # The price to trigger at
                    "sl": float(sl),
                    "tp": float(tp),
                    "magic": 123456,
                    "comment": "Telegram AI Bot (Pending)",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_FOK, 
                }
                result = mt5.order_send(trade_request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    print(f"❌ [Trader] Pending Trade FAILED for TP {tp}. Code: {result.retcode}, Comment: {result.comment}")
                else:
                    print(f"✅ [Trader] Pending Trade PLACED for TP {tp}. Order: {result.order}")

        else:
            print(f"⚠️ [Trader] SKIPPED: Unknown order_type: {order_type_str}")

    except Exception as e:
        print(f"❌ [Trader] An error occurred during trade execution: {e}")
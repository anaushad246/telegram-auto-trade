import MetaTrader5 as mt5
import time
from . import config

# --- UPDATE THIS PATH TO MATCH YOUR VPS ---
# Common paths:
# "C:\Program Files\MetaTrader 5\terminal64.exe"
# "C:\Program Files\OctaFX MetaTrader 5\terminal64.exe"
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"

def connect_to_mt5():
    print(f"📈 [MT5] Connecting to: {MT5_PATH}...")
    
    # 1. Try to initialize with the specific path
    if not mt5.initialize(path=MT5_PATH):
        print(f"⚠️ [MT5] Failed to init with path. Trying default... Error: {mt5.last_error()}")
        
        # 2. Fallback: Try default initialize (searches registry)
        if not mt5.initialize():
            print(f"❌ [MT5] Initialization failed: {mt5.last_error()}")
            return False

    # 3. Ensure we are logged into the correct account
    current_account = mt5.account_info()
    if current_account and current_account.login == config.MT5_LOGIN:
        print(f"✅ [MT5] Already connected to account {config.MT5_LOGIN}.")
    else:
        print(f"🔄 [MT5] Logging in to account {config.MT5_LOGIN}...")
        if not mt5.login(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
            print(f"❌ [MT5] Login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False
            
    print(f"✅ [MT5] Connected successfully to {config.MT5_SERVER}.")
    return True

def shutdown_mt5():
    print("📈 [MT5] Shutting down connection...")
    mt5.shutdown()

def execute_trade_from_json(signal, magic_number):
    """
    Executes or modifies trades based on the parsed signal JSON
    and the group's magic_number.
    """
    try:
        symbol = signal["symbol"]
        action = signal["action"]
        order_type_str = signal["order_type"] 

        # Check if symbol exists
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            print(f"❌ [Trader] Symbol {symbol} not found in MT5.")
            return
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
            time.sleep(1) 

        # --- LOGIC FOR NEW TRADES (BUY/SELL) ---
        if action == "BUY" or action == "SELL":
            sl = signal["sl"]
            tp_list = signal["tp_list"]
            lot_size = config.FIXED_LOT_SIZE
            entry_range = signal.get("entry_range")
            
            family_id = f"signal_{int(time.time())}"
            
            # --- MARKET ORDERS ---
            if order_type_str == "MARKET":
                print(f"📈 [Trader] Processing MARKET order for group {magic_number}.")
                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    print(f"❌ [Trader] Failed to get tick for {symbol}")
                    return
                    
                if action == "BUY": price = tick.ask
                else: price = tick.bid

                # Price Safety Check
                if entry_range:
                    if len(entry_range) == 2: 
                        min_entry, max_entry = min(entry_range), max(entry_range)
                        if not (min_entry <= price <= max_entry):
                            print(f"⚠️ [Trader] SKIPPED: Price {price} outside {min_entry}-{max_entry}.")
                            return
                    elif len(entry_range) == 1:
                        target_price = entry_range[0]
                        if (action == "BUY" and price > target_price) or (action == "SELL" and price < target_price):
                            print(f"⚠️ [Trader] SKIPPED: Price {price} worse than {target_price}.")
                            return

                print(f"📈 [Trader] Placing {len(tp_list)} MARKET trades for {action} {symbol}")
                for tp in tp_list:
                    trade_request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol, "volume": lot_size,
                        "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
                        "price": price, "sl": float(sl), "tp": float(tp),
                        "deviation": 20, "magic": magic_number, "comment": family_id,
                        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK,
                    }
                    result = mt5.order_send(trade_request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE: 
                        print(f"❌ [Trader] FAILED TP {tp}: {result.comment} ({result.retcode})")
                    else: 
                        print(f"✅ [Trader] PLACED TP {tp}. Order: {result.order}")

            # --- PENDING ORDERS ---
            elif order_type_str in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"]:
                print(f"📈 [Trader] Processing PENDING order for group {magic_number}.")
                order_type_map = {
                    "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT, "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT, 
                    "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP, "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP
                }
                mt5_order_type = order_type_map[order_type_str]
                
                if not entry_range:
                    print(f"❌ [Trader] Pending order missing entry price.")
                    return
                trigger_price = entry_range[0]

                for tp in tp_list:
                    trade_request = {
                        "action": mt5.TRADE_ACTION_PENDING,
                        "symbol": symbol, "volume": lot_size,
                        "type": mt5_order_type, "price": float(trigger_price),
                        "sl": float(sl), "tp": float(tp),
                        "magic": magic_number, "comment": family_id,
                        "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK, 
                    }
                    result = mt5.order_send(trade_request)
                    if result.retcode != mt5.TRADE_RETCODE_DONE:
                        print(f"❌ [Trader] FAILED Pending TP {tp}: {result.comment}")
                    else:
                        print(f"✅ [Trader] PLACED Pending TP {tp}. Order: {result.order}")

        # --- MODIFY TRADES ---
        elif action == "MODIFY":
            print(f"📈 [Trader] Processing MODIFY command for {symbol}...")
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                print(f"⚠️ [Trader] No open positions found for {symbol}.")
                return

            # Filter for THIS group
            my_positions = [p for p in positions if p.magic == magic_number]
            if not my_positions:
                print(f"⚠️ [Trader] No positions found for magic {magic_number}.")
                return

            for position in my_positions:
                new_sl, new_tp = position.sl, position.tp
                
                if order_type_str == "BREAK_EVEN":
                    new_sl = position.price_open
                elif order_type_str == "MOVE_SL":
                    new_sl = signal["value"]
                elif order_type_str == "MOVE_TP":
                    new_tp = signal["value"]
                
                if new_sl == position.sl and new_tp == position.tp:
                    continue # No change needed

                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": position.ticket,
                    "sl": float(new_sl),
                    "tp": float(new_tp),
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"✅ [Trader] Modified ticket {position.ticket}")
                else:
                    print(f"❌ [Trader] Modify failed: {result.comment}")

    except Exception as e:
        print(f"❌ [Trader] Execution Error: {e}")

def monitor_automatic_be():
    """
    Monitor logic to move stops to BE when TPs are hit.
    """
    try:
        # 1. Get all open positions
        open_positions = mt5.positions_get()
        if not open_positions: return
        
        open_families = {}
        for pos in open_positions:
            if pos.comment.startswith("signal_"):
                if pos.comment not in open_families: open_families[pos.comment] = []
                open_families[pos.comment].append(pos)

        if not open_families: return

        # 2. Get closed deals (last hour)
        from_date = int(time.time()) - 3600
        to_date = int(time.time())
        deals = mt5.history_deals_get(from_date, to_date)
        if not deals: return
            
        # 3. Find families with hit TPs
        families_closed_by_tp = set()
        for deal in deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT and deal.reason == mt5.DEAL_REASON_TP:
                if deal.comment.startswith("signal_"):
                    families_closed_by_tp.add(deal.comment)

        # 4. Move remaining positions to BE
        families_to_move = set(open_families.keys()).intersection(families_closed_by_tp)
        
        for fam_id in families_to_move:
            for position in open_families[fam_id]:
                entry_price = position.price_open
                
                if abs(position.sl - entry_price) > 0.00001:
                    print(f"📈 [Monitor] Auto-BE for ticket {position.ticket}")
                    request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": position.ticket,
                        "sl": entry_price,
                        "tp": position.tp,
                    }
                    mt5.order_send(request)

    except Exception as e:
        print(f"❌ [Monitor] Error: {e}")
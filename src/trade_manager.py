def connect_to_mt5():
    print("📈 [MT5] Connecting...")
    if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        print(f"❌ [MT5] Initialization failed: {mt5.last_error()}")
        return False
    print(f"✅ [MT5] Connected to {config.MT5_SERVER} as {config.MT5_LOGIN}.")
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
            
            # --- Plan B: Generate a "Family ID" for Auto-BE ---
            family_id = f"signal_{int(time.time())}"
            
            # --- 3a. LOGIC FOR MARKET ORDERS ---
            if order_type_str == "MARKET":
                print(f"📈 [Trader] Processing MARKET order for group {magic_number}.")
                if action == "BUY": price = mt5.symbol_info_tick(symbol).ask
                else: price = mt5.symbol_info_tick(symbol).bid

                # Price Safety Check
                if entry_range:
                    if len(entry_range) == 2: # Range check
                        min_entry, max_entry = min(entry_range), max(entry_range)
                        if not (min_entry <= price <= max_entry):
                            print(f"⚠️ [Trader] SKIPPED: Current price {price} is outside entry range {min_entry}-{max_entry}.")
                            return
                        print(f"✅ [Trader] Price check passed (range): {price} is within {min_entry}-{max_entry}.")
                    elif len(entry_range) == 1: # Single price check
                        target_price = entry_range[0]
                        if (action == "BUY" and price > target_price) or (action == "SELL" and price < target_price):
                            print(f"⚠️ [Trader] SKIPPED: Current price {price} is worse than target entry {target_price}.")
                            return
                        print(f"✅ [Trader] Price check passed (single): {price} is at or better than target {target_price}.")

                print(f"📈 [Trader] Placing {len(tp_list)} MARKET trades for {action} {symbol} @ {price} [Magic: {magic_number}, Family: {family_id}]")
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
                    if result.retcode != mt5.TRADE_RETCODE_DONE: print(f"❌ [Trader] Market Trade FAILED for TP {tp}. Code: {result.retcode}, Comment: {result.comment}")
                    else: print(f"✅ [Trader] Market Trade PLACED for TP {tp}. Order: {result.order}")

            # --- 3b. LOGIC FOR PENDING ORDERS ---
            elif order_type_str in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"]:
                print(f"📈 [Trader] Processing PENDING order for group {magic_number}.")
                order_type_map = {"BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT, "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT, "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP, "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP}
                mt5_order_type = order_type_map[order_type_str]
                if not entry_range or len(entry_range) != 1:
                    print(f"❌ [Trader] SKIPPED: Pending order signal is missing its trigger price.")
                    return
                trigger_price = entry_range[0]

                print(f"📈 [Trader] Placing {len(tp_list)} PENDING trades for {action} {symbol} @ {trigger_price} [Magic: {magic_number}, Family: {family_id}]")
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
                    if result.retcode != mt5.TRADE_RETCODE_DONE: print(f"❌ [Trader] Pending Trade FAILED for TP {tp}. Code: {result.retcode}, Comment: {result.comment}")
                    else: print(f"✅ [Trader] Pending Trade PLACED for TP {tp}. Order: {result.order}")

        # --- LOGIC FOR MODIFYING TRADES (MANUAL SIGNALS) ---
        elif action == "MODIFY":
            print(f"📈 [Trader] Processing MODIFY command for {symbol} [Magic: {magic_number}]...")
            
            # Get all open positions
            positions = mt5.positions_get(symbol=symbol)
            if not positions:
                print(f"⚠️ [Trader] No open positions found for {symbol}.")
                return

            # Filter for positions from THIS GROUP ONLY
            my_group_positions = [p for p in positions if p.magic == magic_number]
            if not my_group_positions:
                print(f"⚠️ [Trader] No open positions found for {symbol} with magic number {magic_number}.")
                return

            modified_count = 0
            for position in my_group_positions:
                new_sl, new_tp = position.sl, position.tp # Start with current values
                
                if order_type_str == "BREAK_EVEN":
                    new_sl = position.price_open
                    if position.sl == new_sl:
                        print(f"⚠️ [Trader] SKIPPED BE for ticket {position.ticket}: SL is already at break-even.")
                        continue
                
                elif order_type_str == "MOVE_SL":
                    new_sl = signal["value"]
                    if position.sl == new_sl:
                        print(f"⚠️ [Trader] SKIPPED Move SL for ticket {position.ticket}: SL is already at {new_sl}.")
                        continue

                elif order_type_str == "MOVE_TP":
                    new_tp = signal["value"]
                    if position.tp == new_tp:
                        print(f"⚠️ [Trader] SKIPPED Move TP for ticket {position.ticket}: TP is already at {new_tp}.")
                        continue
                
                # Send the modification request
                request = {
                    "action": mt5.TRADE_ACTION_SLTP, # Action to modify SL/TP
                    "position": position.ticket,     # The ticket of the trade to modify
                    "sl": new_sl,
                    "tp": new_tp,
                }
                result = mt5.order_send(request)
                if result.retcode != mt5.TRADE_RETCODE_DONE: print(f"❌ [Trader] Modify FAILED for ticket {position.ticket}. Code: {result.retcode}, Comment: {result.comment}")
                else:
                    print(f"✅ [Trader] Modify SUCCESS for ticket {position.ticket}. (SL: {new_sl}, TP: {new_tp})")
                    modified_count += 1
            
            print(f"✅ [Trader] Modify logic completed. {modified_count} trade(s) modified.")

        else:
            print(f"⚠️ [Trader] SKIPPED: Unknown action: {action}")

    except Exception as e:
        print(f"❌ [Trader] An error occurred during trade execution: {e}")

# --- NEW MONITOR FUNCTION FOR AUTOMATIC BE ---
def monitor_automatic_be():
    """
    Plan B: Checks for closed TP1 trades and moves sister trades to BE.
    This function is run by the monitor loop in main.py.
    """
    try:
        # 1. Get all open positions and their family IDs
        open_positions = mt5.positions_get()
        if not open_positions:
            return # No open trades, nothing to do
        
        open_families = {} # key: family_id, value: list of positions
        for pos in open_positions:
            if pos.comment.startswith("signal_"):
                if pos.comment not in open_families:
                    open_families[pos.comment] = []
                open_families[pos.comment].append(pos)

        if not open_families:
            return # No open trades with our comment structure

        # 2. Get recently closed deals (last 1 hour to be safe)
        from_date = int(time.time()) - 3600
        to_date = int(time.time())
        deals = mt5.history_deals_get(from_date, to_date)
        if not deals:
            return # No closed deals recently
            
        # 3. Find families that had a TP hit
        families_closed_by_tp = set()
        for deal in deals:
            # Check if it's a new, processed-by-TP, trade
            if deal.ticket not in processed_deal_tickets and deal.entry == mt5.DEAL_ENTRY_OUT and deal.reason == mt5.DEAL_REASON_TP:
                if deal.comment.startswith("signal_"):
                    families_closed_by_tp.add(deal.comment)
                    processed_deal_tickets.add(deal.ticket) # Mark as processed

        if not families_closed_by_tp:
            return # No new TP hits

        # 4. Find the intersection: families that are STILL OPEN and HAD A TP HIT
        families_to_move_to_be = set(open_families.keys()).intersection(families_closed_by_tp)
        
        if families_to_move_to_be:
            print(f"💡 [Monitor] Auto-BE Triggered for families: {families_to_move_to_be}")
            for fam_id in families_to_move_to_be:
                # Get the sister trades that are still open
                for position_to_modify in open_families[fam_id]:
                    entry_price = position_to_modify.price_open
                    
                    # Only modify if SL is not already at entry
                    if position_to_modify.sl != entry_price:
                        print(f"📈 [Monitor] Moving SL to BE for ticket {position_to_modify.ticket} (Family: {fam_id})")
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": position_to_modify.ticket,
                            "sl": entry_price,
                            "tp": position_to_modify.tp,
                        }
                        result = mt5.order_send(request)
                        if result.retcode != mt5.TRADE_RETCODE_DONE: print(f"❌ [Monitor] Auto-BE FAILED for ticket {position_to_modify.ticket}. Code: {result.retcode}")
                        else: print(f"✅ [Monitor] Auto-BE SUCCESS for ticket {position_to_modify.ticket}.")

    except Exception as e:
        print(f"❌ [Monitor] Error in monitor_automatic_be: {e}")
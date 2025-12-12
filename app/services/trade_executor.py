import time
import MetaTrader5 as mt5
from app.config import config
from app.log_setup import setup_logger
from app.models.signal import TradeSignal
from app.services.mt5_svc import MT5Service

logger = setup_logger("TradeExecutor")

class TradeExecutor:
    def __init__(self, mt5_service: MT5Service):
        self.mt5 = mt5_service

    def execute_signal(self, signal: TradeSignal, magic_number: int):
        try:
            if not self.mt5.connected:
                if not self.mt5.connect():
                    logger.error("Cannot execute signal: MT5 not connected.")
                    return

            symbol = signal.symbol
            action = signal.action

            # Check symbol availability
            if not self.mt5.get_symbol_info(symbol):
                return

            # --- NEW TRADES ---
            if action in ["BUY", "SELL"]:
                self._handle_new_trade(signal, magic_number)
            
            # --- MODIFY TRADES ---
            elif action == "MODIFY":
                self._handle_modify_trade(signal, magic_number)

        except Exception as e:
            logger.error(f"Execution Error: {e}")

    def _handle_new_trade(self, signal: TradeSignal, magic_number: int):
        symbol = signal.symbol
        action = signal.action
        order_type_str = signal.order_type
        
        # Ensure tp_list and entry_range are lists, even if AI returns None
        tp_list = signal.tp_list if signal.tp_list else []
        entry_range = signal.entry_range if signal.entry_range else []
        
        sl = signal.sl
        lot_size = config.FIXED_LOT_SIZE
        family_id = f"signal_{int(time.time())}"

        # ==============================================================================
        # MARKET ORDERS
        # ==============================================================================
        if order_type_str == "MARKET":
            logger.info(f"Processing MARKET order for group {magic_number}.")
            
            symbol_info = self.mt5.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {symbol}")
                return
            
            tick = self.mt5.get_tick(symbol)
            if not tick:
                logger.error(f"Failed to get tick for {symbol}")
                return
                
            if action == "BUY": price = tick.ask
            else: price = tick.bid

            # --- TOLERANCE LOGIC ---
            TOLERANCE = 50.0 * symbol_info.point 
            if "XAU" in symbol or "GOLD" in symbol:
                TOLERANCE = 2.00

            if entry_range:
                if len(entry_range) == 2: 
                    min_entry, max_entry = min(entry_range), max(entry_range)
                    valid_min = min_entry - TOLERANCE
                    valid_max = max_entry + TOLERANCE
                    if not (valid_min <= price <= valid_max):
                        logger.warning(f"SKIPPED: Price {price} outside {valid_min}-{valid_max}.")
                        return
                elif len(entry_range) == 1:
                    target_price = entry_range[0]
                    if action == "BUY":
                        if price > (target_price + TOLERANCE):
                            logger.warning(f"SKIPPED: Price {price} too high above {target_price}.")
                            return
                    elif action == "SELL":
                        if price < (target_price - TOLERANCE):
                            logger.warning(f"SKIPPED: Price {price} too low below {target_price}.")
                            return
                    logger.info(f"Price {price} accepted within tolerance of {target_price}.")

            logger.info(f"Placing {len(tp_list)} MARKET trades for {action} {symbol}")
            for tp in tp_list:
                trade_request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol, "volume": lot_size,
                    "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
                    "price": price, "sl": float(sl), "tp": float(tp),
                    "deviation": 20, "magic": magic_number, "comment": family_id,
                    "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK,
                }
                result = self.mt5.send_order(trade_request)
                if result.retcode != mt5.TRADE_RETCODE_DONE: 
                    logger.error(f"FAILED TP {tp}: {result.comment} ({result.retcode})")
                else: 
                    logger.info(f"PLACED TP {tp}. Order: {result.order}")

        # ==============================================================================
        # PENDING ORDERS (BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP)
        # ==============================================================================
        elif order_type_str in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"]:
            logger.info(f"Processing {order_type_str} order for group {magic_number}.")
            
            if not entry_range or len(entry_range) == 0:
                logger.error(f"Cannot place {order_type_str}: Missing entry price.")
                return

            price = float(entry_range[0])
            
            # --- CRITICAL FIX: CHECK STOPS LEVEL ---
            symbol_info = self.mt5.get_symbol_info(symbol)
            if not symbol_info:
                logger.error(f"Symbol info not found for {symbol}")
                return

            tick = self.mt5.get_tick(symbol)
            if not tick:
                logger.error(f"Tick not found for {symbol}")
                return

            # Broker's minimum stop distance (Stops Level)
            # trade_stops_level is usually in points. We convert to price.
            stops_level_dist = symbol_info.trade_stops_level * symbol_info.point
            # Add a safety buffer (e.g. 10 points)
            min_dist = stops_level_dist + (10 * symbol_info.point)

            current_ask = tick.ask
            current_bid = tick.bid
            
            # Check if pending price is too close to current market price
            is_valid_dist = True
            
            if "BUY" in order_type_str:
                # BUY orders interact with Ask price logic generally, but limits depend on direction
                if order_type_str == "BUY_STOP":
                    # Buy Stop must be ABOVE Ask
                    if price <= (current_ask + min_dist):
                        logger.warning(f"SKIPPED {order_type_str}: Price {price} too close to Ask {current_ask} (Need > {current_ask + min_dist})")
                        is_valid_dist = False
                elif order_type_str == "BUY_LIMIT":
                    # Buy Limit must be BELOW Ask
                    if price >= (current_ask - min_dist):
                        logger.warning(f"SKIPPED {order_type_str}: Price {price} too close to Ask {current_ask} (Need < {current_ask - min_dist})")
                        is_valid_dist = False

            elif "SELL" in order_type_str:
                if order_type_str == "SELL_STOP":
                    # Sell Stop must be BELOW Bid
                    if price >= (current_bid - min_dist):
                        logger.warning(f"SKIPPED {order_type_str}: Price {price} too close to Bid {current_bid} (Need < {current_bid - min_dist})")
                        is_valid_dist = False
                elif order_type_str == "SELL_LIMIT":
                    # Sell Limit must be ABOVE Bid
                    if price <= (current_bid + min_dist):
                        logger.warning(f"SKIPPED {order_type_str}: Price {price} too close to Bid {current_bid} (Need > {current_bid + min_dist})")
                        is_valid_dist = False
            
            if not is_valid_dist:
                return
            # ---------------------------------------

            # Map string to MT5 constant
            mt5_type = None
            if order_type_str == "BUY_LIMIT": mt5_type = mt5.ORDER_TYPE_BUY_LIMIT
            elif order_type_str == "SELL_LIMIT": mt5_type = mt5.ORDER_TYPE_SELL_LIMIT
            elif order_type_str == "BUY_STOP": mt5_type = mt5.ORDER_TYPE_BUY_STOP
            elif order_type_str == "SELL_STOP": mt5_type = mt5.ORDER_TYPE_SELL_STOP
            
            logger.info(f"Placing {len(tp_list)} pending trades at {price} for {symbol}")
            
            for tp in tp_list:
                trade_request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": lot_size,
                    "type": mt5_type,
                    "price": float(price),
                    "sl": float(sl),
                    "tp": float(tp),
                    "deviation": 20,
                    "magic": magic_number,
                    "comment": family_id,
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_RETURN,
                }
                
                result = self.mt5.send_order(trade_request)
                
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"FAILED {order_type_str} TP {tp}: {result.comment} ({result.retcode})")
                else:
                    logger.info(f"PLACED {order_type_str} TP {tp}. Order: {result.order}")

        else:
            logger.error(f"Unrecognized order type: {order_type_str}")

    def _handle_modify_trade(self, signal: TradeSignal, magic_number: int):
        symbol = signal.symbol
        order_type_str = signal.order_type
        
        logger.info(f"Processing MODIFY command for {symbol}...")
        my_positions = self.mt5.get_positions(symbol=symbol, magic=magic_number)
        
        if not my_positions:
            logger.warning(f"No positions found for magic {magic_number}.")
            return

        for position in my_positions:
            new_sl, new_tp = position.sl, position.tp
            
            if order_type_str == "BREAK_EVEN":
                profit_buffer = 0.0
                if "XAU" in symbol: profit_buffer = 0.10
                
                if position.type == mt5.POSITION_TYPE_BUY:
                    new_sl = position.price_open + profit_buffer
                    if new_sl < position.price_open: new_sl = position.price_open
                else:
                    new_sl = position.price_open - profit_buffer
                    if new_sl > position.price_open: new_sl = position.price_open
                    
            elif order_type_str == "MOVE_SL":
                new_sl = signal.value
            elif order_type_str == "MOVE_TP":
                new_tp = signal.value
            
            # Avoid sending unnecessary modification requests
            if abs(new_sl - position.sl) < 1e-5 and abs(new_tp - position.tp) < 1e-5:
                continue 

            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "sl": float(new_sl),
                "tp": float(new_tp),
            }
            result = self.mt5.send_order(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Modified ticket {position.ticket}")
            else:
                logger.error(f"Modify failed: {result.comment}")
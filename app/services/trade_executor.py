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
            order_type_str = signal.order_type

            # Check symbol
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
        sl = signal.sl
        tp_list = signal.tp_list
        lot_size = config.FIXED_LOT_SIZE
        entry_range = signal.entry_range
        
        family_id = f"signal_{int(time.time())}"

        # MARKET ORDERS
        if order_type_str == "MARKET":
            logger.info(f"Processing MARKET order for group {magic_number}.")
            tick = self.mt5.get_tick(symbol)
            if not tick:
                logger.error(f"Failed to get tick for {symbol}")
                return
                
            if action == "BUY": price = tick.ask
            else: price = tick.bid

            # --- TOLERANCE LOGIC ---
            TOLERANCE = 50.0 * tick.point
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

        # PENDING ORDERS
        elif order_type_str in ["BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"]:
            logger.info(f"Processing PENDING order for group {magic_number}.")
            order_type_map = {
                "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT, "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT, 
                "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP, "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP
            }
            mt5_order_type = order_type_map[order_type_str]
            
            if not entry_range:
                logger.error("Pending order missing entry price.")
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
                result = self.mt5.send_order(trade_request)
                if result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"FAILED Pending TP {tp}: {result.comment}")
                else:
                    logger.info(f"PLACED Pending TP {tp}. Order: {result.order}")

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

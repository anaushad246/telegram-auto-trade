import asyncio
import time
import MetaTrader5 as mt5
from app.log_setup import setup_logger
from app.services.trade_executor import TradeExecutor
from app.models.signal import TradeSignal

logger = setup_logger("MonitorWorker")

class MonitorWorker:
    def __init__(self, executor: TradeExecutor):
        self.executor = executor
        self.mt5 = executor.mt5
        self.running = False

    async def start_loop(self):
        self.running = True
        logger.info("Starting automatic BE monitor loop...")
        while self.running:
            try:
                self._check_and_move_be()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            
            # Sleep for 60 seconds (or adjustable)
            await asyncio.sleep(60)

    def _check_and_move_be(self):
        if not self.mt5.connected:
            return

        # 1. Get all open positions
        open_positions = self.mt5.get_positions()
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
        deals = self.mt5.get_history_deals(from_date, to_date)
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
            # We need the magic number to use the executor properly, 
            # but the executor's modify logic filters by magic number.
            # Here we have specific positions.
            # Let's just use the magic number from the first position in the family.
            positions = open_families[fam_id]
            if not positions: continue
            
            magic_number = positions[0].magic
            symbol = positions[0].symbol
            
            # Check if any position in this family needs BE
            needs_update = False
            for position in positions:
                entry_price = position.price_open
                if abs(position.sl - entry_price) > 0.00001:
                    needs_update = True
                    break
            
            if needs_update:
                logger.info(f"Auto-BE triggered for family {fam_id}")
                # Create a signal to trigger the BE logic in executor
                signal = TradeSignal(
                    symbol=symbol,
                    action="MODIFY",
                    order_type="BREAK_EVEN"
                )
                self.executor.execute_signal(signal, magic_number)

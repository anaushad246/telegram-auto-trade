import asyncio
import time
import csv
import os
import MetaTrader5 as mt5
from datetime import datetime
from app.log_setup import setup_logger
from app.services.trade_executor import TradeExecutor
from app.models.signal import TradeSignal

logger = setup_logger("MonitorWorker")

CSV_FILE = "trade_history.csv"

class MonitorWorker:
    def __init__(self, executor: TradeExecutor):
        self.executor = executor
        self.mt5 = executor.mt5
        self.running = False
        self.last_check_time = time.time()

        # Initialize CSV if not exists
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "Time", "Symbol", "Action", "Magic", "Profit", "Reason", "Comment"
                ])

    async def start_loop(self):
        self.running = True
        logger.info("Starting Monitor Loop (Auto-BE + Trade Result Tracking)...")

        while self.running:
            try:
                # 1. Break-even logic
                self._check_and_move_be()

                # 2. Result tracking logic
                self._track_trade_results()

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            await asyncio.sleep(60)  # run every minute

    # =====================================================================================
    # 🎯 TRADE RESULT TRACKING + CSV LOGGING
    # =====================================================================================
    def _track_trade_results(self):
        if not self.mt5.connected:
            return

        to_time = time.time()
        from_time = self.last_check_time
        self.last_check_time = to_time

        deals = self.mt5.get_history_deals(from_time, to_time)

        if deals:
            for deal in deals:
                # Only entry-out deals & trades made by bot
                if deal.entry == mt5.DEAL_ENTRY_OUT and deal.magic > 0:
                    self._log_deal_to_csv(deal)

    def _log_deal_to_csv(self, deal):
        # Determine exit reason
        reason = "MANUAL/OTHER"
        if deal.reason == mt5.DEAL_REASON_TP:
            reason = "TAKE_PROFIT"
        elif deal.reason == mt5.DEAL_REASON_SL:
            reason = "STOP_LOSS"

        deal_time = datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S')
        action = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"

        logger.info(
            f"📊 Trade Closed → {deal.symbol} | Profit: {deal.profit} "
            f"| Reason: {reason} | Magic: {deal.magic}"
        )

        try:
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    deal_time,
                    deal.symbol,
                    action,
                    deal.magic,
                    deal.profit,
                    reason,
                    deal.comment
                ])
        except Exception as e:
            logger.error(f"Failed to write to CSV: {e}")

    # =====================================================================================
    # 🎯 AUTO BREAK-EVEN LOGIC
    # =====================================================================================
    def _check_and_move_be(self):
        if not self.mt5.connected:
            return

        # 1️⃣ Fetch open positions
        open_positions = self.mt5.get_positions()
        if not open_positions:
            return

        # Group by signal family
        open_families = {}
        for pos in open_positions:
            if pos.comment.startswith("signal_"):
                open_families.setdefault(pos.comment, []).append(pos)

        if not open_families:
            return

        # 2️⃣ Fetch closed deals (last hour)
        from_date = int(time.time()) - 3600
        to_date = int(time.time())
        deals = self.mt5.get_history_deals(from_date, to_date)
        if not deals:
            return

        # 3️⃣ Find families where at least one member hit TP
        families_closed_by_tp = set()
        for deal in deals:
            if deal.entry == mt5.DEAL_ENTRY_OUT and deal.reason == mt5.DEAL_REASON_TP:
                if deal.comment.startswith("signal_"):
                    families_closed_by_tp.add(deal.comment)

        # 4️⃣ Which families still have open positions?
        families_to_move = set(open_families.keys()).intersection(families_closed_by_tp)

        # 5️⃣ Move remaining trades to BE
        for fam_id in families_to_move:
            positions = open_families[fam_id]
            if not positions:
                continue

            magic_number = positions[0].magic
            symbol = positions[0].symbol

            # Check if any position needs a BE move
            needs_update = False
            for position in positions:
                entry_price = position.price_open
                if abs(position.sl - entry_price) > 0.00001:
                    needs_update = True
                    break

            if needs_update:
                logger.info(f"Auto-BE triggered for signal family: {fam_id}")

                signal = TradeSignal(
                    symbol=symbol,
                    action="MODIFY",
                    order_type="BREAK_EVEN"
                )

                self.executor.execute_signal(signal, magic_number)

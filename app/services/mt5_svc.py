import MetaTrader5 as mt5
from app.config import config
from app.log_setup import setup_logger

logger = setup_logger("MT5Service")

class MT5Service:
    def __init__(self):
        self.connected = False

    def connect(self) -> bool:
        logger.info(f"Connecting to: {config.MT5_PATH}...")
        
        # 1. Try to initialize with the specific path
        if not mt5.initialize(path=config.MT5_PATH):
            logger.warning(f"Failed to init with path. Trying default... Error: {mt5.last_error()}")
            
            # 2. Fallback: Try default initialize
            if not mt5.initialize():
                logger.error(f"Initialization failed: {mt5.last_error()}")
                return False

        # 3. Ensure we are logged into the correct account
        current_account = mt5.account_info()
        if current_account and current_account.login == config.MT5_LOGIN:
            logger.info(f"Already connected to account {config.MT5_LOGIN}.")
            self.connected = True
        else:
            logger.info(f"Logging in to account {config.MT5_LOGIN}...")
            if not mt5.login(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
                logger.error(f"Login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
            self.connected = True
            
        logger.info(f"Connected successfully to {config.MT5_SERVER}.")
        return True

    def shutdown(self):
        logger.info("Shutting down connection...")
        mt5.shutdown()
        self.connected = False

    def get_symbol_info(self, symbol: str):
        info = mt5.symbol_info(symbol)
        if not info:
            logger.error(f"Symbol {symbol} not found.")
            return None
        if not info.visible:
            mt5.symbol_select(symbol, True)
        return info

    def get_tick(self, symbol: str):
        return mt5.symbol_info_tick(symbol)

    def send_order(self, request: dict):
        return mt5.order_send(request)

    def get_positions(self, symbol: str = None, magic: int = None):
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions is None:
            return []

        if magic:
            return [p for p in positions if p.magic == magic]
        return list(positions)
        
    def get_history_deals(self, from_date, to_date):
        return mt5.history_deals_get(from_date, to_date)

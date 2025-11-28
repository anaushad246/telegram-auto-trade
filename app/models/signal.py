from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class TradeSignal(BaseModel):
    symbol: str
    action: Literal["BUY", "SELL", "MODIFY"]
    order_type: Literal[
        "MARKET", 
        "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP",
        "BREAK_EVEN", "MOVE_SL", "MOVE_TP"
    ]
    entry_range: Optional[List[float]] = Field(default=None, description="[min, max] or [target]")
    sl: Optional[float] = None
    tp_list: Optional[List[float]] = Field(default_factory=list)
    value: Optional[float] = Field(default=None, description="New value for MODIFY actions")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "XAUUSD",
                "action": "BUY",
                "order_type": "MARKET",
                "entry_range": [2000.50, 2001.00],
                "sl": 1995.00,
                "tp_list": [2005.00, 2010.00]
            }
        }

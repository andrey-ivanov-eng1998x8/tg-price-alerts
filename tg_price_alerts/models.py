from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetType(str, Enum):
    CRYPTO = "crypto"
    STOCK = "stock"


class ConditionType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PCT_CHANGE_UP = "pct_change_up"
    PCT_CHANGE_DOWN = "pct_change_down"


@dataclass(frozen=True, slots=True)
class PriceTick:
    symbol: str
    source: str
    price: float
    timestamp: datetime
    volume_24h: Optional[float] = None
    # raw payload kept for debugging weird exchange response quirks
    raw: Optional[dict] = None


@dataclass
class AlertRule:
    id: str
    symbol: str
    condition: ConditionType
    target_value: float
    window_seconds: int = 0
    cooldown_seconds: int = 3600
    # if True, disabled automatically after first alert firing
    one_shot: bool = False
    last_triggered_at: Optional[datetime] = None
    last_price: Optional[float] = None
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class TriggeredAlert:
    rule_id: str
    symbol: str
    condition: ConditionType
    current_price: float
    target_value: float
    baseline_price: Optional[float]
    triggered_at: datetime
    message: str

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, model_validator

from tg_price_alerts.models import ConditionType


class TelegramConfig(BaseModel):
    bot_token: str = ""
    chat_id: str
    thread_id: Optional[int] = None
    timeout_seconds: float = 10.0
    silent_notifications: bool = False

    @model_validator(mode="after")
    def check_token(self) -> "TelegramConfig":
        if not self.bot_token:
            env_token = os.environ.get("TG_BOT_TOKEN", "").strip()
            if not env_token:
                raise ValueError("bot_token must be set in config or via TG_BOT_TOKEN env var")
            self.bot_token = env_token
        return self


class TargetConfig(BaseModel):
    id: Optional[str] = None
    type: ConditionType
    target: float
    cooldown_seconds: int = Field(default=3600, ge=10)
    window_seconds: int = Field(default=0, ge=0)
    one_shot: bool = False


class WatcherConfig(BaseModel):
    symbol: str
    # coingecko, binance, yahoo, etc.
    source: str = "binance"
    poll_interval: int = Field(default=30, ge=3)
    targets: List[TargetConfig] = Field(default_factory=list)


class DatabaseConfig(BaseModel):
    path: str = "data/alerts.db"
    retention_days: int = 7


class AppConfig(BaseModel):
    telegram: TelegramConfig
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    watchers: List[WatcherConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def assign_target_ids(self) -> "AppConfig":
        for watcher in self.watchers:
            sym = watcher.symbol.lower().replace("/", "_").replace("-", "_")
            for idx, target in enumerate(watcher.targets, start=1):
                if not target.id:
                    # synthetic id if user omitted it in yaml
                    target.id = f"{sym}_{target.type.value}_{idx}"
        return self


def load_config(path: str | Path) -> AppConfig:
    """Load and validate yaml config, resolving env overrides."""
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config file not found at: {config_path.resolve()}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f) or {}

    return AppConfig.model_validate(raw)

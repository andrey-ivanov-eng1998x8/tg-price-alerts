import logging
import time
from typing import List
from tg_price_alerts.models import AlertRule, AlertType
from tg_price_alerts.fetchers import PriceFetcher
from tg_price_alerts.db import Database
from tg_price_alerts.notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def _format_price(val: float) -> str:
    if val >= 100:
        return f"{val:,.2f}"
    elif val >= 1:
        return f"{val:,.4f}"
    else:
        return f"{val:,.6f}"


class AlertEngine:
    """Evaluates configured price threshold and percentage movement rules."""

    def __init__(self, rules: List[AlertRule], db: Database, fetcher: PriceFetcher, notifier: TelegramNotifier):
        self.rules = rules
        self.db = db
        self.fetcher = fetcher
        self.notifier = notifier

    def evaluate_rule(self, rule: AlertRule, current_price: float) -> bool:
        if self.db.is_on_cooldown(rule.id, rule.cooldown_minutes * 60):
            return False

        triggered = False
        msg = ""
        curr_str = _format_price(current_price)

        if rule.alert_type == AlertType.THRESHOLD_ABOVE:
            if current_price >= rule.target_value:
                triggered = True
                target_str = _format_price(rule.target_value)
                msg = f"🚀 <b>{rule.symbol}</b> crossed ABOVE\nPrice: <code>{curr_str}</code>\nTarget: <code>{target_str}</code> ({rule.source})"

        elif rule.alert_type == AlertType.THRESHOLD_BELOW:
            if current_price <= rule.target_value:
                triggered = True
                target_str = _format_price(rule.target_value)
                msg = f"🔻 <b>{rule.symbol}</b> dropped BELOW\nPrice: <code>{curr_str}</code>\nTarget: <code>{target_str}</code> ({rule.source})"

        elif rule.alert_type == AlertType.PCT_CHANGE_WINDOW:
            window_secs = (rule.window_minutes or 60) * 60
            base_price = self.db.get_oldest_price_in_window(rule.symbol, window_secs)
            if base_price and base_price > 0:
                pct = ((current_price - base_price) / base_price) * 100.0
                target_pct = rule.target_value  # e.g. 5.0 for +5% or -3.0 for -3%

                if target_pct > 0 and pct >= target_pct:
                    triggered = True
                    msg = (
                        f"📈 <b>{rule.symbol}</b> pumped <b>+{pct:.2f}%</b> in {rule.window_minutes}m\n"
                        f"Price: <code>{curr_str}</code> (from {_format_price(base_price)})"
                    )
                elif target_pct < 0 and pct <= target_pct:
                    triggered = True
                    msg = (
                        f"📉 <b>{rule.symbol}</b> dumped <b>{pct:.2f}%</b> in {rule.window_minutes}m\n"
                        f"Price: <code>{curr_str}</code> (from {_format_price(base_price)})"
                    )

        if triggered and msg:
            logger.info(f"alert fired: {rule.id} ({rule.symbol})")
            sent = self.notifier.send(msg, chat_id=rule.chat_id)
            if sent:
                self.db.update_cooldown(rule.id)
                return True
        return False

    def tick(self):
        active_rules = [r for r in self.rules if r.enabled]
        if not active_rules:
            return

        # Fetch each symbol once per tick
        symbols_to_fetch = set((r.source, r.symbol) for r in active_rules)
        prices = {}

        for source, symbol in symbols_to_fetch:
            price = self.fetcher.fetch(source, symbol)
            if price is not None:
                prices[(source, symbol)] = price
                self.db.insert_price(symbol, source, price)

        for rule in active_rules:
            key = (rule.source, rule.symbol)
            if key in prices:
                try:
                    self.evaluate_rule(rule, prices[key])
                except Exception as e:
                    logger.exception(f"error evaluating rule {rule.id}: {e}")

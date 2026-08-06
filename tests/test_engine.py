import pytest
from datetime import datetime, timezone, timedelta
from tg_price_alerts.models import AlertRule, AlertType, PricePoint
from tg_price_alerts.engine import evaluate_rule, CooldownTracker, calculate_pct_change


def test_target_price_above_trigger():
    rule = AlertRule(
        id="btc-target-100k",
        symbol="BTC/USDT",
        alert_type=AlertType.TARGET_ABOVE,
        target_value=100000.0,
        cooldown_minutes=60,
    )
    price = PricePoint(symbol="BTC/USDT", price=100050.0, timestamp=datetime.now(timezone.utc))
    assert evaluate_rule(rule, current_price=price, history=[]) is True


def test_target_price_above_not_met():
    rule = AlertRule(
        id="btc-target-100k",
        symbol="BTC/USDT",
        alert_type=AlertType.TARGET_ABOVE,
        target_value=100000.0,
        cooldown_minutes=60,
    )
    price = PricePoint(symbol="BTC/USDT", price=99999.5, timestamp=datetime.now(timezone.utc))
    assert evaluate_rule(rule, current_price=price, history=[]) is False


def test_target_price_below_trigger():
    rule = AlertRule(
        id="eth-dip",
        symbol="ETH/USDT",
        alert_type=AlertType.TARGET_BELOW,
        target_value=2500.0,
        cooldown_minutes=30,
    )
    price = PricePoint(symbol="ETH/USDT", price=2499.0, timestamp=datetime.now(timezone.utc))
    assert evaluate_rule(rule, current_price=price, history=[]) is True


def test_pct_change_rolling_window():
    now = datetime(2025, 2, 1, 10, 30, tzinfo=timezone.utc)
    history = [
        PricePoint(symbol="SOL/USDT", price=180.0, timestamp=now - timedelta(minutes=45)),
        PricePoint(symbol="SOL/USDT", price=190.0, timestamp=now - timedelta(minutes=20)),
        PricePoint(symbol="SOL/USDT", price=195.0, timestamp=now - timedelta(minutes=5)),
    ]
    current = PricePoint(symbol="SOL/USDT", price=207.0, timestamp=now)

    # 180 to 207 is +15%
    rule = AlertRule(
        id="sol-pump-10pct",
        symbol="SOL/USDT",
        alert_type=AlertType.PCT_CHANGE_UP,
        target_value=10.0,  # 10%
        window_minutes=60,
        cooldown_minutes=120,
    )

    # print(f"calculated: {calculate_pct_change(history, current, 60)}")
    assert evaluate_rule(rule, current_price=current, history=history) is True


def test_pct_change_ignores_points_outside_window():
    now = datetime(2025, 2, 1, 10, 30, tzinfo=timezone.utc)
    history = [
        # Older than 30 min window, should be skipped
        PricePoint(symbol="SOL/USDT", price=100.0, timestamp=now - timedelta(minutes=45)),
        PricePoint(symbol="SOL/USDT", price=198.0, timestamp=now - timedelta(minutes=15)),
    ]
    current = PricePoint(symbol="SOL/USDT", price=200.0, timestamp=now)

    rule = AlertRule(
        id="sol-pump-short",
        symbol="SOL/USDT",
        alert_type=AlertType.PCT_CHANGE_UP,
        target_value=5.0,
        window_minutes=30,
        cooldown_minutes=30,
    )
    # 198 to 200 is ~1.01%, not enough for 5%
    assert evaluate_rule(rule, current_price=current, history=history) is False


def test_empty_history_does_not_crash_pct_rule():
    now = datetime.now(timezone.utc)
    current = PricePoint(symbol="BTC/USDT", price=95000.0, timestamp=now)
    rule = AlertRule(
        id="btc-pct",
        symbol="BTC/USDT",
        alert_type=AlertType.PCT_CHANGE_DOWN,
        target_value=3.0,
        window_minutes=15,
    )
    assert evaluate_rule(rule, current_price=current, history=[]) is False


def test_cooldown_blocks_immediate_repeat():
    tracker = CooldownTracker()
    now = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
    
    tracker.record_fire("rule-1", now)
    
    # 10 minutes later on a 30m cooldown
    assert tracker.is_cooling_down("rule-1", 30, now + timedelta(minutes=10)) is True
    # 31 minutes later
    assert tracker.is_cooling_down("rule-1", 30, now + timedelta(minutes=31)) is False


# FIXME: if system clock hops back, cooldown tracker should still clamp correctly
def test_cooldown_untracked_rule():
    tracker = CooldownTracker()
    now = datetime.now(timezone.utc)
    assert tracker.is_cooling_down("unknown-rule", 30, now) is False

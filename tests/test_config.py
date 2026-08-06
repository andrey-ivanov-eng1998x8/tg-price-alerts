from pathlib import Path
import pytest
from tg_price_alerts.config import load_config, ConfigError

SAMPLE_YAML = """
telegram:
  bot_token: "123456:ABC-DEF"
  chat_id: 987654321
poll_interval_sec: 15
db_path: "data/alerts.db"
rules:
  - symbol: "BTCUSDT"
    kind: "crypto"
    condition: "above"
    target_price: 65000.0
  - symbol: "AAPL"
    kind: "stock"
    condition: "pct_change"
    threshold_pct: 3.5
    window_minutes: 60
"""


def test_load_basic_yaml(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(SAMPLE_YAML)

    cfg = load_config(cfg_file)
    # print(f"loaded: {cfg}")
    assert cfg.telegram.bot_token == "123456:ABC-DEF"
    assert cfg.telegram.chat_id == 987654321
    assert cfg.poll_interval_sec == 15
    assert len(cfg.rules) == 2
    assert cfg.rules[0].symbol == "BTCUSDT"
    assert cfg.rules[0].target_price == 65000.0
    assert cfg.rules[1].threshold_pct == 3.5


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/never_there.yaml")


def test_missing_telegram_section(tmp_path: Path):
    bad_yaml = "poll_interval_sec: 30\nrules: []\n"
    cfg_file = tmp_path / "bad.yaml"
    cfg_file.write_text(bad_yaml)

    with pytest.raises(ConfigError, match="telegram"):
        load_config(cfg_file)


def test_env_var_overrides(tmp_path: Path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(SAMPLE_YAML)

    monkeypatch.setenv("TG_BOT_TOKEN", "override_token_999")
    monkeypatch.setenv("TG_CHAT_ID", "112233")
    monkeypatch.setenv("ALERT_POLL_INTERVAL", "5")

    cfg = load_config(cfg_file)
    assert cfg.telegram.bot_token == "override_token_999"
    assert cfg.telegram.chat_id == 112233
    assert cfg.poll_interval_sec == 5


def test_invalid_rule_condition(tmp_path: Path):
    bad_yaml = """
    telegram:
      bot_token: "dummy"
      chat_id: 123
    rules:
      - symbol: "ETHUSDT"
        kind: "crypto"
        condition: "moon_soon"
        target_price: 4000
    """
    cfg_file = tmp_path / "invalid_cond.yaml"
    cfg_file.write_text(bad_yaml)

    with pytest.raises(ConfigError, match="condition"):
        load_config(cfg_file)


def test_pct_change_missing_window(tmp_path: Path):
    bad_yaml = """
    telegram:
      bot_token: "dummy"
      chat_id: 123
    rules:
      - symbol: "TSLA"
        kind: "stock"
        condition: "pct_change"
        threshold_pct: 5.0
    """
    cfg_file = tmp_path / "no_window.yaml"
    cfg_file.write_text(bad_yaml)

    with pytest.raises(ConfigError, match="window_minutes"):
        load_config(cfg_file)


def test_target_price_missing_for_threshold(tmp_path: Path):
    bad_yaml = """
    telegram:
      bot_token: "dummy"
      chat_id: 123
    rules:
      - symbol: "BTCUSDT"
        kind: "crypto"
        condition: "below"
    """
    cfg_file = tmp_path / "no_price.yaml"
    cfg_file.write_text(bad_yaml)

    with pytest.raises(ConfigError, match="target_price"):
        load_config(cfg_file)


def test_default_cooldown_fallback(tmp_path: Path):
    cfg_file = tmp_path / "default_cd.yaml"
    cfg_file.write_text(SAMPLE_YAML)
    cfg = load_config(cfg_file)
    # should default to 30 mins when omitted in rule block
    assert cfg.rules[0].cooldown_minutes == 30

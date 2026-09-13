# tg_price_alerts

I needed something dead simple to keep track of a few crypto prices and stock drops without running heavy services or paying for alert subscriptions. This runs as a standalone daemon, fetches current prices from public endpoints (Binance, CoinGecko, Yahoo Finance), and pings my Telegram bot when conditions match.

State and last-triggered timestamps are stored in a local SQLite file so it doesn't spam alerts on every tick.

## Quick Start

```bash
git clone https://github.com/username/tg_price_alerts.git
cd tg_price_alerts
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Copy the example config and adjust values:

```bash
cp config.example.yaml config.yaml
```

Run the daemon:

```bash
python -m tg_price_alerts -c config.yaml
```

## Running as a systemd service

Here is what I use on a Debian box:

```ini
# /etc/systemd/system/tg-price-alerts.service
[Unit]
Description=Telegram Price Alert Daemon
After=network.target

[Service]
Type=simple
User=alex
WorkingDirectory=/opt/tg_price_alerts
ExecStart=/opt/tg_price_alerts/.venv/bin/python -m tg_price_alerts -c /opt/tg_price_alerts/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tg-price-alerts
```

## Supported Sources & Rules

- `binance`: specify `pair` (e.g. `BTCUSDT`, `ETHUSDT`).
- `coingecko`: specify `coin_id` (e.g. `solana`, `bitcoin`). Useful for coins not on Binance.
- `yahoo`: specify `ticker` (e.g. `AAPL`, `NVDA`, `VOO`).

Rule conditions:
- `target_above`: fires when price crosses above value.
- `target_below`: fires when price drops below value.
- `pct_change_24h`: fires when absolute 24h percentage movement exceeds this number.
- `cooldown_sec`: override global cooldown before the same rule can fire again.

## Tests

```bash
pytest
```

<!-- last-sync: 2026-09-13 -->

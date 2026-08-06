import pytest
import httpx
from tg_price_alerts.fetchers import (
    BinanceFetcher,
    CoinGeckoFetcher,
    YahooFinanceFetcher,
    FetchError,
    RateLimitError,
)


class DummyResponse:
    def __init__(self, json_data=None, text="", status_code=200):
        self._json_data = json_data
        self.text = text
        self.status_code = status_code

    def json(self):
        if self._json_data is None:
            raise ValueError("No JSON object could be decoded")
        return self._json_data

    def raise_for_status(self):
        if self.status_code == 429:
            raise httpx.HTTPStatusError("Rate limited", request=None, response=self)
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("HTTP error", request=None, response=self)


def test_binance_fetcher_parses_price(monkeypatch):
    fetcher = BinanceFetcher()

    def mock_get(url, *args, **kwargs):
        assert "symbol=BTCUSDT" in url
        return DummyResponse({"symbol": "BTCUSDT", "price": "68412.30"})

    monkeypatch.setattr(httpx, "get", mock_get)
    price = fetcher.fetch_price("BTC/USDT")
    assert price == 68412.30


def test_coingecko_fetcher_parses_simple_price(monkeypatch):
    fetcher = CoinGeckoFetcher()

    def mock_get(url, *args, **kwargs):
        assert "ids=monero" in url
        return DummyResponse({"monero": {"usd": 164.85}})

    monkeypatch.setattr(httpx, "get", mock_get)
    price = fetcher.fetch_price("monero")
    assert price == 164.85


def test_yahoo_fetcher_parses_chart_meta(monkeypatch):
    fetcher = YahooFinanceFetcher()
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 224.52,
                        "symbol": "AAPL",
                    }
                }
            ],
            "error": None,
        }
    }

    def mock_get(url, *args, **kwargs):
        return DummyResponse(payload)

    monkeypatch.setattr(httpx, "get", mock_get)
    price = fetcher.fetch_price("AAPL")
    assert price == 224.52


def test_fetcher_raises_rate_limit_on_429(monkeypatch):
    fetcher = BinanceFetcher()

    def mock_get(*args, **kwargs):
        return DummyResponse(status_code=429)

    monkeypatch.setattr(httpx, "get", mock_get)
    with pytest.raises(RateLimitError):
        fetcher.fetch_price("ETH/USDT")


def test_fetcher_handles_garbage_json(monkeypatch):
    fetcher = YahooFinanceFetcher()

    # HTML error page returned under 200 by some captive proxies
    def mock_get(*args, **kwargs):
        return DummyResponse(json_data=None, text="<html>Cloudflare block</html>")

    monkeypatch.setattr(httpx, "get", mock_get)
    with pytest.raises(FetchError):
        fetcher.fetch_price("NVDA")

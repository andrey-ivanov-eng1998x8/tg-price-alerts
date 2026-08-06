import logging
from typing import Optional, Dict
import httpx

logger = logging.getLogger(__name__)


class PriceFetcher:
    """Fetches live ticker prices from public endpoints without API keys."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        # Yahoo blocks default python/httpx user agents
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.client = httpx.Client(timeout=timeout, headers=headers)

    def fetch_binance(self, symbol: str) -> Optional[float]:
        pair = symbol.replace("/", "").replace("-", "").upper()
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return float(data["price"])
        except Exception as e:
            logger.warning(f"failed to fetch {symbol} from binance: {e}")
            return None

    def fetch_kraken(self, pair: str) -> Optional[float]:
        clean_pair = pair.replace("/", "").replace("-", "").upper()
        url = f"https://api.kraken.com/0/public/Ticker?pair={clean_pair}"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("error"):
                logger.warning(f"kraken error for {pair}: {payload['error']}")
                return None
            result = payload["result"]
            first_key = next(iter(result))
            return float(result[first_key]["c"][0])
        except Exception as e:
            logger.warning(f"failed to fetch {pair} from kraken: {e}")
            return None

    def fetch_yahoo(self, symbol: str) -> Optional[float]:
        # TODO: handle crumb token if yahoo starts returning 401 again
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}?interval=1m&range=1d"
        try:
            resp = self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            meta = data["chart"]["result"][0]["meta"]
            # regularMarketPrice is preferred, fallback to chartPreviousClose if off-hours
            price = meta.get("regularMarketPrice")
            if price is None:
                price = meta.get("chartPreviousClose")
            # print(f"DEBUG yahoo: {symbol} -> {price}")
            return float(price) if price is not None else None
        except Exception as e:
            logger.warning(f"failed to fetch {symbol} from yahoo finance: {e}")
            return None

    def fetch(self, source: str, symbol: str) -> Optional[float]:
        src = source.lower()
        if src == "binance":
            return self.fetch_binance(symbol)
        elif src == "kraken":
            return self.fetch_kraken(symbol)
        elif src in ("yahoo", "yfinance", "stock"):
            return self.fetch_yahoo(symbol)
        else:
            logger.error(f"unknown price source: {source}")
            return None

    def close(self):
        self.client.close()

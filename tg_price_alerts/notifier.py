import logging
import time
import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, default_chat_id: str):
        self.bot_token = bot_token
        self.default_chat_id = str(default_chat_id) if default_chat_id else ""
        self.client = httpx.Client(timeout=10.0)

    def send(self, message: str, chat_id: str = None) -> bool:
        target_chat = chat_id or self.default_chat_id
        if not self.bot_token or not target_chat:
            logger.warning("telegram bot token or chat_id is missing, skipping alert")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        # simple retry once on 429 flood control
        for attempt in range(2):
            try:
                resp = self.client.post(url, json=payload)
                if resp.status_code == 429:
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 3)
                    logger.warning(f"telegram rate limit hit, sleeping {retry_after}s")
                    time.sleep(retry_after + 0.5)
                    continue
                resp.raise_for_status()
                return True
            except Exception as e:
                # Avoid logging full URL containing bot token
                logger.error(f"failed sending tg notification: {type(e).__name__} - {e}")
                return False
        return False

    def close(self):
        self.client.close()

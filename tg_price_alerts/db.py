import sqlite3
import time
from pathlib import Path
from typing import Optional, List, Tuple


class Database:
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self.init_schema()
        return self._conn

    def init_schema(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS price_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                price REAL NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_symbol_created 
                ON price_points(symbol, created_at);

            CREATE TABLE IF NOT EXISTS alert_cooldowns (
                alert_id TEXT PRIMARY KEY,
                last_triggered_at REAL NOT NULL
            );
        """)
        self._conn.commit()

    def insert_price(self, symbol: str, source: str, price: float, ts: Optional[float] = None):
        ts = ts or time.time()
        conn = self.connect()
        with conn:
            conn.execute(
                "INSERT INTO price_points (symbol, source, price, created_at) VALUES (?, ?, ?, ?)",
                (symbol.upper(), source.lower(), float(price), ts),
            )

    def get_oldest_price_in_window(self, symbol: str, window_seconds: int) -> Optional[float]:
        cutoff = time.time() - window_seconds
        conn = self.connect()
        cur = conn.execute(
            """
            SELECT price FROM price_points
            WHERE symbol = ? AND created_at >= ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (symbol.upper(), cutoff),
        )
        row = cur.fetchone()
        return row["price"] if row else None

    def is_on_cooldown(self, alert_id: str, cooldown_seconds: int) -> bool:
        conn = self.connect()
        cur = conn.execute(
            "SELECT last_triggered_at FROM alert_cooldowns WHERE alert_id = ?",
            (alert_id,),
        )
        row = cur.fetchone()
        if not row:
            return False
        return (time.time() - row["last_triggered_at"]) < cooldown_seconds

    def update_cooldown(self, alert_id: str, ts: Optional[float] = None):
        ts = ts or time.time()
        conn = self.connect()
        with conn:
            conn.execute(
                "INSERT INTO alert_cooldowns (alert_id, last_triggered_at) VALUES (?, ?) "
                "ON CONFLICT(alert_id) DO UPDATE SET last_triggered_at = excluded.last_triggered_at",
                (alert_id, ts),
            )

    def purge_old_data(self, max_age_seconds: int = 86400 * 3):
        # Keep DB small so it doesn't eat up the tiny VPS disk
        cutoff = time.time() - max_age_seconds
        conn = self.connect()
        with conn:
            conn.execute("DELETE FROM price_points WHERE created_at < ?", (cutoff,))

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

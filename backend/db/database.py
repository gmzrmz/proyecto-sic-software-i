import sqlite3
import threading
from pathlib import Path
from typing import Optional

import config

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS metrics (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                instance      TEXT    NOT NULL,
                timestamp     TEXT    NOT NULL,
                cpu_pct       REAL    NOT NULL,
                ram_pct       REAL    NOT NULL,
                net_bytes_in  INTEGER NOT NULL,
                net_bytes_out INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp);

            CREATE TABLE IF NOT EXISTS narratives (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT    NOT NULL,
                text      TEXT    NOT NULL,
                level     TEXT    NOT NULL CHECK(level IN ('normal', 'atencion', 'critico'))
            );
            CREATE INDEX IF NOT EXISTS idx_narratives_ts ON narratives(timestamp);

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()


def check_db() -> bool:
    try:
        with _lock:
            conn = _connect()
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return True
    except Exception:
        return False


def insert_metrics_batch(rows: list) -> None:
    with _lock:
        conn = _connect()
        conn.executemany(
            "INSERT INTO metrics "
            "(instance, timestamp, cpu_pct, ram_pct, net_bytes_in, net_bytes_out) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        conn.close()


def insert_metric(
    instance: str,
    timestamp: str,
    cpu_pct: float,
    ram_pct: float,
    net_bytes_in: int,
    net_bytes_out: int,
) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO metrics "
            "(instance, timestamp, cpu_pct, ram_pct, net_bytes_in, net_bytes_out) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (instance, timestamp, cpu_pct, ram_pct, net_bytes_in, net_bytes_out),
        )
        conn.commit()
        conn.close()


def get_latest_metric() -> Optional[dict]:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None


def get_metrics_by_hours(hours: int) -> list[dict]:
    with _lock:
        conn = _connect()
        # Timestamps are stored as ISO 8601 UTC strings (YYYY-MM-DDTHH:MM:SSZ).
        # SQLite's strftime with the same format enables correct string comparison.
        rows = conn.execute(
            "SELECT * FROM metrics "
            "WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', ? || ' hours') "
            "ORDER BY timestamp ASC",
            (f"-{hours}",),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def get_simulator_state() -> dict:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'sim_mode'"
        ).fetchone()
        conn.close()
    return {"mode": row["value"] if row else "normal"}


def save_simulator_state(mode: str) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('sim_mode', ?)", (mode,)
        )
        conn.commit()
        conn.close()


def clear_all() -> dict:
    with _lock:
        conn = _connect()
        metrics_count   = conn.execute("SELECT COUNT(*) FROM metrics").fetchone()[0]
        narrative_count = conn.execute("SELECT COUNT(*) FROM narratives").fetchone()[0]
        conn.execute("DELETE FROM metrics")
        conn.execute("DELETE FROM narratives")
        conn.commit()
        conn.close()
    return {"metrics": metrics_count, "narratives": narrative_count}


def insert_narrative(timestamp: str, text: str, level: str) -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            "INSERT INTO narratives (timestamp, text, level) VALUES (?, ?, ?)",
            (timestamp, text, level),
        )
        conn.commit()
        conn.close()


def get_latest_narrative() -> Optional[dict]:
    with _lock:
        conn = _connect()
        row = conn.execute(
            "SELECT * FROM narratives ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return dict(row) if row else None


def get_recent_narratives(limit: int = 5) -> list[dict]:
    with _lock:
        conn = _connect()
        rows = conn.execute(
            "SELECT * FROM narratives ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

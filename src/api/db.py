"""Thin Snowflake query layer for the API.

Routes call query(); tests monkeypatch it. One lazily created connection per
process — Snowflake connections are thread-safe for independent cursors, and
uvicorn workers each get their own.
"""

import logging
import threading

from dotenv import load_dotenv
from snowflake.connector import DatabaseError, DictCursor

from connectors.snowflake_client import get_connection

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn = None


def _connect() -> None:
    global _conn
    load_dotenv()
    _conn = get_connection(schema="MARTS")


def _connection():
    global _conn
    with _lock:
        if _conn is None or _conn.is_closed():
            _connect()
        return _conn


def query(sql: str, params: dict | None = None) -> list[dict]:
    for attempt in range(2):
        conn = _connection()
        cur = conn.cursor(DictCursor)
        try:
            cur.execute(sql, params or {})
            return [{k.lower(): v for k, v in row.items()} for row in cur.fetchall()]
        except DatabaseError:
            cur.close()
            if attempt == 0:
                # Session likely expired; force reconnect and retry once.
                logger.warning("Snowflake query failed, reconnecting")
                with _lock:
                    _connect()
            else:
                raise
        finally:
            try:
                cur.close()
            except Exception:
                pass
    return []  # unreachable

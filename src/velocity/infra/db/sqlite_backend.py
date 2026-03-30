"""
SQLite Database Backend.
Local development persistence utilizing `aiosqlite` for zero-configuration, 
schema-compliant testing across Agent architectures.
"""

import logging
from typing import Any

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore

from velocity.infra import IDatabaseBackend

logger = logging.getLogger(__name__)


class SQLiteBackend(IDatabaseBackend):
    """
    Implements standard SQL persistence relying on a localized file.
    Does not natively support concurrency scaling across multiple Gunicorn workers well,
    but ensures perfect schema parity for Local Dev parity.
    """

    def __init__(self, db_path: str):
        if aiosqlite is None:
            raise ImportError("Please install `aiosqlite` to use SQLite backend.")
        # E.g. 'sqlite:///data.db' -> 'data.db'
        self.db_path = db_path.replace("sqlite:///", "") if db_path.startswith("sqlite") else db_path

    async def execute(self, query: str, parameters: dict[str, Any] | None = None) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, parameters or {})
            await db.commit()

    async def fetch_one(self, query: str, parameters: dict[str, Any] | None = None) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters or {}) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_all(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, parameters or {}) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def health_check(self) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"SQLite Health Check Failed: {e}")
            return False

import logging
import os
import random
import time
from typing import List, Optional, Tuple

import aiosqlite

logger = logging.getLogger("discord.quotes.db")


class QuoteManager:
    def __init__(self, db_path: str = "db/quotes.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self.db_connection = None

    def _ensure_db_dir(self):
        dirname = os.path.dirname(self.db_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

    async def get_db(self):
        if self.db_connection is None:
            self.db_connection = await aiosqlite.connect(self.db_path)
            await self.db_connection.execute("PRAGMA journal_mode=WAL")
            await self.db_connection.execute("PRAGMA synchronous=NORMAL")
            await self.db_connection.execute("PRAGMA cache_size=-64000")
        return self.db_connection

    async def initialize(self):
        db = await self.get_db()
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                content TEXT,
                timestamp TEXT,
                channel_id INTEGER,
                adder_user_id INTEGER,
                added_timestamp INTEGER,
                uses INTEGER DEFAULT 0
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_guild_user ON quotes(guild_id, user_id)")
        await db.commit()
        logger.info("Quote database initialized (Persistent Mode).")

    # ==========================================================================
    # RANDOM
    # ==========================================================================
    async def get_random_quote(
        self, guild_id: int, user_id: Optional[int] = None
    ) -> Optional[Tuple]:
        db = await self.get_db()

        where_clauses = ["guild_id = ?"]
        params = [guild_id]

        if user_id:
            where_clauses.append("user_id = ?")
            params.append(user_id)

        where_str = " AND ".join(where_clauses)

        cursor = await db.execute(f"SELECT id FROM quotes WHERE {where_str}", tuple(params))
        rows = await cursor.fetchall()

        if not rows:
            return None

        random_id_tuple = random.choice(rows)
        target_id = random_id_tuple[0]

        fetch_query = """
            SELECT id, content, timestamp, channel_id,
                   user_id, adder_user_id, added_timestamp, uses
            FROM quotes
            WHERE id = ?
        """

        cursor = await db.execute(fetch_query, (target_id,))
        row = await cursor.fetchone()

        if row:
            await db.execute("UPDATE quotes SET uses = uses + 1 WHERE id = ?", (target_id,))
            await db.commit()

        return row

    # ==========================================================================
    # ADD
    # ==========================================================================
    async def add_quote(
        self,
        guild_id: int,
        user_id: int,
        adder_id: int,
        content: str,
        channel_id: int,
        timestamp: int,
    ) -> bool:
        current_time = int(time.time())
        db = await self.get_db()

        cursor = await db.execute(
            "SELECT id FROM quotes WHERE guild_id = ? AND user_id = ? AND content = ?",
            (guild_id, user_id, content),
        )
        if await cursor.fetchone():
            return False

        await db.execute(
            """INSERT INTO quotes (guild_id, user_id, content, timestamp, channel_id, adder_user_id, added_timestamp, uses) 
               VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
            (guild_id, user_id, content, str(timestamp), channel_id, adder_id, current_time),
        )
        await db.commit()
        return True

    # ==========================================================================
    # 📜 Standard Getters (Updated to use self.get_db())
    # ==========================================================================
    async def get_quotes_for_list(self, guild_id: int, user_id: int) -> List[Tuple]:
        db = await self.get_db()
        query = "SELECT content, added_timestamp, adder_user_id, uses FROM quotes WHERE guild_id = ? AND user_id = ? ORDER BY added_timestamp DESC"
        async with db.execute(query, (guild_id, user_id)) as cursor:
            return await cursor.fetchall()

    async def get_quotes_for_deletion(self, guild_id: int, user_id: int) -> List[Tuple]:
        db = await self.get_db()
        query = "SELECT content, added_timestamp, adder_user_id, uses, id FROM quotes WHERE guild_id = ? AND user_id = ? ORDER BY added_timestamp DESC"
        async with db.execute(query, (guild_id, user_id)) as cursor:
            return await cursor.fetchall()

    async def get_top_quotes(
        self, guild_id: int, user_id: Optional[int] = None, limit: int = 10
    ) -> List[Tuple]:
        db = await self.get_db()
        query = "SELECT content, user_id, uses FROM quotes WHERE guild_id = ? AND uses > 0"
        params = [guild_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY uses DESC LIMIT ?"
        params.append(limit)
        async with db.execute(query, tuple(params)) as cursor:
            return await cursor.fetchall()

    async def delete_quote(self, quote_id: int) -> bool:
        db = await self.get_db()
        cursor = await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        await db.commit()
        return cursor.rowcount > 0

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

    def _ensure_db_dir(self):
        dirname = os.path.dirname(self.db_path)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)

    async def initialize(self):
        """Creates tables and indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
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

            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_guild_user ON quotes(guild_id, user_id)"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_uses ON quotes(uses DESC)")
            await db.commit()
            logger.info("Quote database initialized.")

    # ==========================================================================
    # ➕ ADD
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
        """Returns True if saved, False if duplicate."""
        current_time = int(time.time())

        async with aiosqlite.connect(self.db_path) as db:
            # Check duplication
            cursor = await db.execute(
                "SELECT id FROM quotes WHERE guild_id = ? AND user_id = ? AND content = ?",
                (guild_id, user_id, content),
            )
            if await cursor.fetchone():
                return False

            await db.execute(
                """
                INSERT INTO quotes (
                    guild_id, user_id, content, timestamp, 
                    channel_id, adder_user_id, added_timestamp, uses
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (guild_id, user_id, content, str(timestamp), channel_id, adder_id, current_time),
            )
            await db.commit()
            return True

    # ==========================================================================
    # 🔍 GET (Single/Random)
    # ==========================================================================
    async def get_random_quote(
        self, guild_id: int, user_id: Optional[int] = None
    ) -> Optional[Tuple]:
        """
        Fetches a random quote using OFFSET method (O(N) Scan)
        """
        async with aiosqlite.connect(self.db_path) as db:
            where_clauses = ["guild_id = ?", "content NOT LIKE '%http%'"]
            params = [guild_id]

            if user_id:
                where_clauses.append("user_id = ?")
                params.append(user_id)

            where_str = " AND ".join(where_clauses)

            # Count how many valid quotes exist
            count_query = f"SELECT COUNT(*) FROM quotes WHERE {where_str}"
            async with db.execute(count_query, tuple(params)) as cursor:
                row = await cursor.fetchone()
                total_count = row[0] if row else 0

            if total_count == 0:
                return None

            # Pick a random index in Python
            random_offset = random.randint(0, total_count - 1)

            # Jump directly to that index
            fetch_query = f"""
                SELECT id, content, timestamp, channel_id,
                       user_id, adder_user_id, added_timestamp, uses
                FROM quotes
                WHERE {where_str}
                LIMIT 1 OFFSET ?
            """
            # Add the offset to the params list
            fetch_params = params + [random_offset]

            async with db.execute(fetch_query, tuple(fetch_params)) as cursor:
                row = await cursor.fetchone()

            if row:
                # Increment usage
                await db.execute("UPDATE quotes SET uses = uses + 1 WHERE id = ?", (row[0],))
                await db.commit()

            return row

    # ==========================================================================
    # 📜 GET (Lists/Pagination)
    # ==========================================================================
    async def get_quotes_for_list(self, guild_id: int, user_id: int) -> List[Tuple]:
        """
        Used for !9uplist.
        Returns: (content, added_timestamp, adder_user_id, uses)
        """
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT content, added_timestamp, adder_user_id, uses
                FROM quotes
                WHERE guild_id = ? AND user_id = ?
                ORDER BY added_timestamp DESC
            """
            async with db.execute(query, (guild_id, user_id)) as cursor:
                return await cursor.fetchall()

    async def get_quotes_for_deletion(self, guild_id: int, user_id: int) -> List[Tuple]:
        """
        Used for !9updel. Matches the exact columns needed for DeleteQuoteView.
        Returns: (content, added_timestamp, adder_user_id, uses, id)
        """
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT content, added_timestamp, adder_user_id, uses, id
                FROM quotes
                WHERE guild_id = ? AND user_id = ?
                ORDER BY added_timestamp DESC
            """
            async with db.execute(query, (guild_id, user_id)) as cursor:
                return await cursor.fetchall()

    # ==========================================================================
    # 🏆 GET (Leaderboards)
    # ==========================================================================
    async def get_top_quotes(
        self, guild_id: int, user_id: Optional[int] = None, limit: int = 10
    ) -> List[Tuple]:
        """
        Used for !9uptop.
        Returns: (content, user_id, uses)
        """
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT content, user_id, uses
                FROM quotes
                WHERE guild_id = ? AND uses > 0
            """
            params = [guild_id]

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)

            query += " ORDER BY uses DESC LIMIT ?"
            params.append(limit)

            async with db.execute(query, tuple(params)) as cursor:
                return await cursor.fetchall()

    # ==========================================================================
    # 🗑️ DELETE
    # ==========================================================================
    async def delete_quote(self, quote_id: int) -> bool:
        """Deletes a quote by ID. Returns True if something was deleted."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            await db.commit()
            return cursor.rowcount > 0

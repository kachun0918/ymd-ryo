import random

import aiosqlite
import discord
from discord.ext import commands

DB_PATH = "db/aliases.db"


async def initialize():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS aliases (
                guild_id INTEGER,
                alias_name TEXT,
                target_user_id INTEGER,
                added_by INTEGER,
                PRIMARY KEY (guild_id, alias_name, target_user_id)
            )
        """)
        await db.commit()


class AliasedGlobal(commands.Converter):
    async def convert(self, ctx, argument: str) -> discord.Member:
        try:
            member_converter = commands.MemberConverter()
            return await member_converter.convert(ctx, argument)
        except commands.MemberNotFound:
            pass

        clean_alias = argument.lower()
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT target_user_id FROM aliases WHERE guild_id = ? AND alias_name = ?",
                (ctx.guild.id, clean_alias),
            )
            rows = await cursor.fetchall()

        if not rows:
            raise commands.MemberNotFound(argument)

        (target_id,) = random.choice(rows)

        member = ctx.guild.get_member(target_id)
        if not member:
            try:
                member = await ctx.guild.fetch_member(target_id)
            except discord.NotFound:
                raise commands.MemberNotFound(argument)

        return member

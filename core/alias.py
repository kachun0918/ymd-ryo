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


async def add_alias_link(guild_id: int, alias_name: str, target_user_id: int, added_by: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO aliases (guild_id, alias_name, target_user_id, added_by) VALUES (?, ?, ?, ?)",
                (guild_id, alias_name, target_user_id, added_by),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_alias_adder(guild_id: int, alias_name: str, target_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT added_by FROM aliases WHERE guild_id = ? AND alias_name = ? AND target_user_id = ?",
            (guild_id, alias_name, target_user_id),
        )
        return await cursor.fetchone()


async def remove_alias_link(guild_id: int, alias_name: str, target_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM aliases WHERE guild_id = ? AND alias_name = ? AND target_user_id = ?",
            (guild_id, alias_name, target_user_id),
        )
        await db.commit()


async def list_alias_links(guild_id: int, target_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT alias_name FROM aliases WHERE guild_id = ? AND target_user_id = ?",
            (guild_id, target_user_id),
        )
        return await cursor.fetchall()


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

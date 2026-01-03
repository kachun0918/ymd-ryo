import aiosqlite
import discord
from discord.ext import commands

from core.alias import DB_PATH, initialize
from core.config import settings
from core.server_settings import server_settings
from core.ui import UI


class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await initialize()

    @commands.command(name="alias")
    async def add_alias(self, ctx, target: discord.Member, alias_name: str):
        clean_name = alias_name.lower()

        if clean_name in ["me", "bot", "all"]:
            return await ctx.send(embed=UI.warn("Invalid Alias", "That name is reserved."))

        async with aiosqlite.connect(DB_PATH) as db:
            try:
                await db.execute(
                    "INSERT INTO aliases (guild_id, alias_name, target_user_id, added_by) VALUES (?, ?, ?, ?)",
                    (ctx.guild.id, clean_name, target.id, ctx.author.id),
                )
                await db.commit()
                await ctx.send(
                    embed=UI.success(
                        "Alias Added", f"Linked `{clean_name}` → **{target.display_name}**"
                    )
                )
            except aiosqlite.IntegrityError:
                await ctx.send(
                    embed=UI.warn(
                        "Already Exists",
                        f"**{target.display_name}** is already linked to `{clean_name}`.",
                    )
                )

    @commands.command(name="unalias")
    async def remove_alias(self, ctx, target: discord.Member, alias_name: str):
        clean_name = alias_name.lower()

        async with aiosqlite.connect(DB_PATH) as db:
            # 1. Fetch the alias first to see who made it
            cursor = await db.execute(
                "SELECT added_by FROM aliases WHERE guild_id = ? AND alias_name = ? AND target_user_id = ?",
                (ctx.guild.id, clean_name, target.id),
            )
            row = await cursor.fetchone()

            if not row:
                return await ctx.send(embed=UI.warn("Not Found", "That alias link does not exist."))

            added_by_id = row[0]

            # 2. Permission Check
            is_creator = ctx.author.id == added_by_id
            is_owner = ctx.author.id == settings.OWNER_ID

            # Check Admin Role from settings
            admin_role_name = server_settings.get_val(ctx.guild.id, "admin_role")
            is_admin = False
            if admin_role_name:
                role = discord.utils.get(ctx.author.roles, name=admin_role_name)
                if role:
                    is_admin = True

            if ctx.author.guild_permissions.administrator:
                is_admin = True

            if not (is_creator or is_owner or is_admin):
                return await ctx.send(
                    embed=UI.error(
                        "Permission Denied",
                        "Only the original creator or an Admin can delete this alias.",
                    )
                )

            # 3. Delete
            await db.execute(
                "DELETE FROM aliases WHERE guild_id = ? AND alias_name = ? AND target_user_id = ?",
                (ctx.guild.id, clean_name, target.id),
            )
            await db.commit()

            await ctx.send(
                embed=UI.success(
                    "Alias Removed", f"Unlinked `{clean_name}` from **{target.display_name}**"
                )
            )

    @commands.command(name="listalias")
    async def list_aliases(self, ctx, target: discord.Member):
        """See all aliases for a user."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT alias_name FROM aliases WHERE guild_id = ? AND target_user_id = ?",
                (ctx.guild.id, target.id),
            )
            rows = await cursor.fetchall()

        if not rows:
            return await ctx.send(
                embed=UI.info(f"Aliases for {target.display_name}", "None found.")
            )

        # Make the list look nice
        alias_list = ", ".join([f"`{row[0]}`" for row in rows])
        await ctx.send(embed=UI.info(f"Aliases for {target.display_name}", alias_list))


async def setup(bot):
    await bot.add_cog(Alias(bot))

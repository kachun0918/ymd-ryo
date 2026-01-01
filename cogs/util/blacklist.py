import logging

import discord
from discord.ext import commands

from core.blacklist import blacklist_store
from core.iam import is_owner
from core.ui import UI

logger = logging.getLogger("bot.cogs.blacklist")


class Blacklist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- COMMAND: !blacklist ---
    @commands.command(hidden=True)
    @is_owner()
    async def blacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.add_block(ctx.guild.id, user.id, cmd):
            await ctx.send(
                embed=UI.success("Blacklisted", f"Blacklisted {user.name} from {ctx.prefix}{cmd}")
            )
        else:
            await ctx.send(
                embed=UI.warn(
                    "Blacklist existed",
                    f"**{user.name}** is already blacklisted from {ctx.prefix}{cmd}.",
                )
            )

    # --- COMMAND: !unblacklist ---
    @commands.command(hidden=True)
    @is_owner()
    async def unblacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.remove_block(ctx.guild.id, user.id, cmd):
            await ctx.send(
                embed=UI.success(
                    "Unblacklisted", f"Unblacklisted {user.name} from {ctx.prefix}{cmd}"
                )
            )
        else:
            await ctx.send(
                embed=UI.warn(
                    "User is not blacklisted",
                    f"**{user.name}** was not blacklisted from `{ctx.prefix}{cmd}`.",
                )
            )

    # --- COMMAND: !viewblacklist ---
    @commands.command(name="viewblacklist", hidden=True)
    @is_owner()
    async def view_blacklist(self, ctx):
        gid = str(ctx.guild.id)
        guild_data = blacklist_store.data.get(gid, {})

        if not guild_data:
            await ctx.send(embed=UI.info("Server blacklist", "Currently empty."))
            return

        desc = ""
        for uid, cmds in guild_data.items():
            user = self.bot.get_user(int(uid))
            name = user.name if user else f"ID: {uid}"
            desc += f"**{name}**: `{', '.join(cmds)}`\n"

        await ctx.send(embed=UI.info("Server blacklist", desc))


async def setup(bot):
    await bot.add_cog(Blacklist(bot))

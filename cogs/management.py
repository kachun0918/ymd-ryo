import logging
import os
import re

import discord
from discord.ext import commands

from core.blacklist import blacklist_store
from core.iam import is_owner
from core.server_settings import server_settings

logger = logging.getLogger("discord.management")


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _success_embed(self, action: str, cog_name: str):
        return discord.Embed(
            title="System Update",
            description=f"✅ Successfully {action} extension: **{cog_name}**",
            color=discord.Color.green(),
        )

    @commands.Cog.listener()
    async def on_command(self, ctx):
        cog_name = ctx.cog.__class__.__name__ if ctx.cog else "Unknown"
        logger.info(
            f"[{cog_name}] {ctx.author.display_name} (ID: {ctx.author.id}) triggered {ctx.command.name}"
        )

    # --- COMMAND: !reload ---
    @commands.command(hidden=True)
    @is_owner()
    async def reload(self, ctx, extension: str):
        cog_path = f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        try:
            await self.bot.reload_extension(cog_path)
            await ctx.send(embed=self._success_embed("reloaded", cog_path))
            logger.info(f"Extension {cog_path} reloaded by {ctx.author}")
        except Exception as e:
            raise e

    # --- COMMAND: !load ---
    @commands.command(hidden=True)
    @is_owner()
    async def load(self, ctx, extension: str):
        cog_path = f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        try:
            await self.bot.load_extension(cog_path)
            await ctx.send(embed=self._success_embed("loaded", cog_path))
            logger.info(f"Extension {cog_path} loaded by {ctx.author}")
        except Exception as e:
            raise e

    # --- COMMAND: !unload ---
    @commands.command(hidden=True)
    @is_owner()
    async def unload(self, ctx, extension: str):
        cog_path = f"cogs.{extension}" if not extension.startswith("cogs.") else extension

        if "management" in cog_path:
            await ctx.send("⚠️ **Safety Warning:** You cannot unload the management module!")
            return

        try:
            await self.bot.unload_extension(cog_path)
            await ctx.send(embed=self._success_embed("unloaded", cog_path))
            logger.info(f"Extension {cog_path} unloaded by {ctx.author}")
        except Exception as e:
            raise e

    # --- COMMAND: !list ---
    @commands.command(name="list", hidden=True)
    @is_owner()
    async def list_cogs(self, ctx):
        loaded_extensions = list(self.bot.extensions.keys())
        desc = "\n".join([f"• `{ext}`" for ext in loaded_extensions]) or "No extensions loaded."

        await ctx.send(
            embed=discord.Embed(
                title="Active Modules", description=desc, color=discord.Color.blue()
            )
        )

    # ------ BLACKLIST COMMANDS ------#

    # --- COMMAND: !blacklist ---
    @commands.command(hidden=True)
    @is_owner()
    async def blacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.add_block(ctx.guild.id, user.id, cmd):
            await ctx.send(embed=self._success_embed("blacklisted", f"{user.name} from !{cmd}"))
        else:
            await ctx.send(f"⚠️ **{user.name}** is already blacklisted.")

    # --- COMMAND: !unblacklist ---
    @commands.command(hidden=True)
    @is_owner()
    async def unblacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.remove_block(ctx.guild.id, user.id, cmd):
            await ctx.send(embed=self._success_embed("unblacklisted", f"{user.name} from !{cmd}"))
        else:
            await ctx.send(f"⚠️ **{user.name}** was not blacklisted from `!{cmd}`.")

    # --- COMMAND: !viewblacklist ---
    @commands.command(name="viewblacklist", hidden=True)
    @is_owner()
    async def view_blacklist(self, ctx):
        gid = str(ctx.guild.id)
        guild_data = blacklist_store.data.get(gid, {})

        if not guild_data:
            await ctx.send("✅ The blacklist is empty for this server.")
            return

        desc = ""
        for uid, cmds in guild_data.items():
            user = self.bot.get_user(int(uid))
            name = user.name if user else f"ID: {uid}"
            desc += f"**{name}**: `{', '.join(cmds)}`\n"

        await ctx.send(
            embed=discord.Embed(
                title="⛔ Server Blacklist",
                description=desc,
                color=discord.Color.dark_red(),
            )
        )

    # --- COMMAND: !setprefix ---
    @commands.command(hidden=True)
    @is_owner()
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 5:
            await ctx.send("❌ Prefix is too long.")
            return

        server_settings.set_val(ctx.guild.id, "prefix", new_prefix)

        await ctx.send(embed=self._success_embed("updated prefix", f"New prefix is `{new_prefix}`"))

    # --- COMMAND: !viewlogs ---
    # --- COMMAND: !viewlogs ---
    @commands.command(name="logs", hidden=True)
    @is_owner()
    async def view_logs(self, ctx, lines: int = 10):
        log_file_path = "logs/discord.log"

        if not os.path.exists(log_file_path):
            await ctx.send("❌ Log file not found.")
            return

        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:]

            output_text = ""

            # Regex: [Date Time] [Level] [Logger] File:Line |? Message
            log_pattern = re.compile(
                r"^\[.*? (\d{2}:\d{2}:\d{2})\] \[.*?\] \[.*?\] .*?:\d+\s*(?:\|)?\s*(.*)$"
            )

            for line in last_lines:
                clean_line = line.strip()
                if not clean_line:
                    continue

                # Parse the line
                match = log_pattern.match(clean_line)

                if match:
                    time_str = match.group(1)  # e.g., "02:37:20"
                    msg_str = match.group(2)  # e.g., "💾 Saved quote..."
                else:
                    # Fallback for tracebacks, etc.
                    time_str = "??"
                    msg_str = clean_line

                # Truncate message
                if len(msg_str) > 70:
                    msg_str = msg_str[:67] + "..."

                # Format: `Time` Message
                output_text += f"`{time_str}` {msg_str}\n"

            if not output_text:
                await ctx.send("📂 Log file is empty.")
                return

            await ctx.send(f"**Last {lines} Log Entries:**\n{output_text}")

        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
            await ctx.send("❌ An error occurred while reading the logs.")


async def setup(bot):
    await bot.add_cog(Management(bot))

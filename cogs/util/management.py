import asyncio
import logging
import os

from discord.ext import commands

from core.iam import is_owner
from core.server_settings import server_settings
from core.ui import UI

logger = logging.getLogger("discord.management")


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _resolve_cog_path(self, partial_name: str) -> str:
        if partial_name.startswith("cogs."):
            return partial_name

        target_file = f"{partial_name}.py"

        for root, dirs, files in os.walk("cogs"):
            if target_file in files:
                path = os.path.join(root, partial_name)
                return path.replace(os.sep, ".")

            if partial_name in dirs:
                path = os.path.join(root, partial_name)
                return path.replace(os.sep, ".")

        return f"cogs.{partial_name}"

    @commands.Cog.listener()
    async def on_command(self, ctx):
        cog_name = ctx.cog.__class__.__name__ if ctx.cog else "Unknown"
        logger.info(f"[{cog_name}] {ctx.author.display_name} triggered {ctx.command.name}")

    # --- COMMAND: !reload ---
    @commands.command(hidden=True)
    @is_owner()
    async def reload(self, ctx, extension: str):
        full_path = self._resolve_cog_path(extension)
        try:
            await self.bot.reload_extension(full_path)
            cog_name = full_path.replace("cogs.", "").replace(".", "/")
            await ctx.send(embed=UI.success("Reloaded", f"Module **{cog_name}** is active."))
            logger.info(f"Extension {full_path} reloaded by {ctx.author}")
        except Exception as e:
            await ctx.send(embed=UI.error("Reload Failed", str(e)))

    # --- COMMAND: !load ---
    @commands.command(hidden=True)
    @is_owner()
    async def load(self, ctx, extension: str):
        full_path = self._resolve_cog_path(extension)
        try:
            await self.bot.load_extension(full_path)
            cog_name = full_path.replace("cogs.", "").replace(".", "/")
            await ctx.send(embed=UI.success("Loaded", f"Module **{cog_name}** is active."))
            logger.info(f"Extension {full_path} loaded by {ctx.author}")
        except commands.ExtensionAlreadyLoaded:
            await ctx.send(embed=UI.warn(f"Module **{extension}** is already active."))
        except Exception as e:
            await ctx.send(embed=UI.error("Load Failed", str(e)))

    # --- COMMAND: !unload ---
    @commands.command(hidden=True)
    @is_owner()
    async def unload(self, ctx, extension: str):
        full_path = self._resolve_cog_path(extension)

        # Safety check
        if "management" in full_path:
            await ctx.send(embed=UI.warn("You cannot unload the management module!"))
            return

        try:
            await self.bot.unload_extension(full_path)
            cog_name = full_path.replace("cogs.", "").replace(".", "/")
            await ctx.send(embed=UI.success("Unloaded", f"Module **{cog_name}** deactivated."))
            logger.info(f"Extension {full_path} unloaded by {ctx.author}")
        except Exception as e:
            await ctx.send(embed=UI.error("Unload Failed", str(e)))

    # --- COMMAND: !listcogs ---
    @commands.command(name="listcogs", hidden=True)
    @is_owner()
    async def list_cogs(self, ctx):
        loaded_extensions = list(self.bot.extensions.keys())
        clean_list = []
        for ext in loaded_extensions:
            name = ext.replace("cogs.", "").replace(".", "/")
            clean_list.append(f"• `{name}`")

        desc = "\n".join(clean_list) or "No extensions loaded."
        await ctx.send(embed=UI.info("Active Modules", desc))

    # --- COMMAND: !setprefix ---
    @commands.command(hidden=True)
    @is_owner()
    async def setprefix(self, ctx, new_prefix: str):
        if len(new_prefix) > 5:
            await ctx.send(embed=UI.warn("Prefix is too long."))
            return

        server_settings.set_val(ctx.guild.id, "prefix", new_prefix)
        await ctx.send(embed=UI.success("Prefix updated", f"New prefix is `{new_prefix}`"))

    # --- COMMAND: !logs ---
    @commands.command(name="logs", hidden=True)
    @is_owner()
    async def view_logs(self, ctx, lines: int = 15):
        log_file_path = "logs/discord.log"
        if not os.path.exists(log_file_path):
            await ctx.send(embed=UI.error("File Error", "Log file not found."))
            return

        def read_file():
            with open(log_file_path, "r", encoding="utf-8") as f:
                return f.readlines()[-lines:]

        try:
            last_lines = await asyncio.to_thread(read_file)

            output = "".join(last_lines)
            if len(output) > 1900:
                output = output[-1900:]  # Truncate if huge

            if not output.strip():
                await ctx.send(embed=UI.info("Logs", "Log file is empty."))
                return

            await ctx.send(f"**Last {lines} Log Entries:**\n```log\n{output}```")
        except Exception as e:
            await ctx.send(embed=UI.error("Log Error", str(e)))


async def setup(bot):
    await bot.add_cog(Management(bot))

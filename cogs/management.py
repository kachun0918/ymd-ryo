import logging
import discord
from discord.ext import commands
from core.blacklist import blacklist_store
from core.server_settings import server_settings
from core.iam import is_owner

# We keep the logger for INFO messages (like "Extension loaded")
logger = logging.getLogger("bot.cogs.management")


class Management(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _success_embed(self, action: str, cog_name: str):
        return discord.Embed(
            title="System Update",
            description=f"✅ Successfully {action} extension: **{cog_name}**",
            color=discord.Color.green(),
        )

    # ---------------------------------------------------------
    # ✂️ REMOVED: cog_command_error
    # ✂️ REMOVED: _error_embed
    # Reason: The Global ErrorHandler in 'cogs/errorhandler.py'
    # now handles silence (stealth) and formatting for us.
    # ---------------------------------------------------------

    # --- COMMAND: !reload ---
    @commands.command(hidden=True)
    @is_owner()
    async def reload(self, ctx, extension: str):
        cog_path = (
            f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        )
        try:
            await self.bot.reload_extension(cog_path)
            await ctx.send(embed=self._success_embed("reloaded", cog_path))
            logger.info(f"Extension {cog_path} reloaded by {ctx.author}")
        except Exception as e:
            # Raising triggers the Global Handler
            raise e

    # --- COMMAND: !load ---
    @commands.command(hidden=True)
    @is_owner()
    async def load(self, ctx, extension: str):
        cog_path = (
            f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        )
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
        cog_path = (
            f"cogs.{extension}" if not extension.startswith("cogs.") else extension
        )

        if "management" in cog_path:
            await ctx.send(
                "⚠️ **Safety Warning:** You cannot unload the management module!"
            )
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
        desc = (
            "\n".join([f"• `{ext}`" for ext in loaded_extensions])
            or "No extensions loaded."
        )

        await ctx.send(
            embed=discord.Embed(
                title="Active Modules", description=desc, color=discord.Color.blue()
            )
        )

    # --- BLACKLIST COMMANDS ---
    @commands.command(hidden=True)
    @is_owner()
    async def blacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.add_block(ctx.guild.id, user.id, cmd):
            await ctx.send(
                embed=self._success_embed("blacklisted", f"{user.name} from !{cmd}")
            )
        else:
            await ctx.send(f"⚠️ **{user.name}** is already blacklisted.")

    @commands.command(hidden=True)
    @is_owner()
    async def unblacklist(self, ctx, user: discord.User, command_name: str):
        cmd = command_name.lower()
        if blacklist_store.remove_block(ctx.guild.id, user.id, cmd):
            await ctx.send(
                embed=self._success_embed("unblacklisted", f"{user.name} from !{cmd}")
            )
        else:
            await ctx.send(f"⚠️ **{user.name}** was not blacklisted from `!{cmd}`.")

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

    @commands.command(hidden=True)
    @is_owner()
    async def setprefix(self, ctx, new_prefix: str):
        """Changes the bot prefix for this server."""
        if len(new_prefix) > 5:
            await ctx.send("❌ Prefix is too long.")
            return

        # 👇 Use the generic setter
        server_settings.set_val(ctx.guild.id, "prefix", new_prefix)

        await ctx.send(
            embed=self._success_embed("updated prefix", f"New prefix is `{new_prefix}`")
        )


async def setup(bot):
    await bot.add_cog(Management(bot))

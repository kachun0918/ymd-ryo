import discord
import logging
from discord.ext import commands

logger = logging.getLogger("bot.errorhandler")


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # 1. IGNORE LOCAL HANDLERS
        if hasattr(ctx.command, "on_error"):
            return

        error = getattr(error, "original", error)

        # 2. IGNORE "COMMAND NOT FOUND"
        if isinstance(error, commands.CommandNotFound):
            return

        # 3. SILENCE STEALTH CHECK (Integrates with Management)
        # If a user is not owner, or is blacklisted, we do NOTHING.
        # This keeps the bot silent/invisible to them.
        if isinstance(
            error, (commands.CheckFailure, commands.NotOwner, commands.MissingRole)
        ):
            return

        # 4. MISSING ARGUMENTS (Integrates with Management)
        # Handles the case where you forget to type the extension name
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"⚠️ **Missing Parameter**: `{error.param.name}`\n"
                f"Usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
            )
            return

        # 5. REAL ERRORS
        logger.error(f"Ignoring exception in command {ctx.command}:", exc_info=error)

        embed = discord.Embed(
            title="❌ Unexpected Error",
            description=f"An error occurred while running `{ctx.command}`.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))

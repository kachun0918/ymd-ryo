import logging

import discord
from discord.ext import commands

logger = logging.getLogger("bot.errorhandler")


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # IGNORE LOCAL HANDLERS
        if hasattr(ctx.command, "on_error"):
            return
        error = getattr(error, "original", error)

        # IGNORE "COMMAND NOT FOUND"
        if isinstance(error, commands.CommandNotFound):
            return

        # SILENCE STEALTH CHECK
        # If a user is not owner, or is blacklisted, we do NOTHING.
        if isinstance(error, (commands.CheckFailure, commands.NotOwner, commands.MissingRole)):
            return

        # MISSING ARGUMENTS
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="⚠️ Missing Parameter",
                description=f"You forgot to include `{error.param.name}`.",
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
            )
            await ctx.send(embed=embed)
            return

        # RATE LIMIT (COOLDOWN)
        if isinstance(error, commands.CommandOnCooldown):
            seconds = f"{error.retry_after:.2f}"
            embed = discord.Embed(
                title="⏳ Cooldown",
                description=f"Please wait **{seconds}s** before using this command again.",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
            return

        # CONCURRENCY LIMIT
        if isinstance(error, commands.MaxConcurrencyReached):
            embed = discord.Embed(
                title="🚦 Traffic Jam",
                description="Another user is checking the CCTV right now.\nPlease wait a moment for them to finish.",
                color=discord.Color.yellow(),
            )
            await ctx.send(embed=embed)
            return

        # REAL UNEXPECTED ERRORS
        logger.error(f"Ignoring exception in command {ctx.command}:", exc_info=error)
        embed = discord.Embed(
            title="❌ Unexpected Error",
            description=f"An error occurred while running `{ctx.command}`.",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))

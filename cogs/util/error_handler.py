import logging

from discord.ext import commands

from core.ui import UI

logger = logging.getLogger("bot.errorhandler")


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # 1. IGNORE LOCAL HANDLERS
        if hasattr(ctx.command, "on_error"):
            return

        # Get the real error if it's wrapped
        error = getattr(error, "original", error)

        # 2. IGNORE "COMMAND NOT FOUND"
        if isinstance(error, commands.CommandNotFound):
            return

        # 3. SILENCE STEALTH CHECKS (Permissions)
        if isinstance(error, (commands.CheckFailure, commands.NotOwner, commands.MissingRole)):
            return

        # 4. MISSING ARGUMENTS
        if isinstance(error, commands.MissingRequiredArgument):
            embed = UI.warn("Missing Parameter", f"You forgot to include `{error.param.name}`.")
            embed.add_field(
                name="Usage",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
            )
            await ctx.send(embed=embed)
            return

        # 5. USER NOT FOUND
        if isinstance(error, (commands.UserNotFound, commands.MemberNotFound)):
            await ctx.send(embed=UI.warn("User Not Found", f"User **{error.argument}** not found."))
            return

        # 6. RATE LIMIT (COOLDOWN)
        if isinstance(error, commands.CommandOnCooldown):
            seconds = f"{error.retry_after:.2f}"
            await ctx.send(
                embed=UI.info(
                    "⏳ Cooldown", f"Please wait **{seconds}s** before using this command again."
                )
            )
            return

        # 7. CONCURRENCY LIMIT
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(
                embed=UI.warn(
                    "🚦 Traffic Jam\nAnother user is using this command right now. Please wait a moment."
                )
            )
            return

        # 8. REAL UNEXPECTED ERRORS
        logger.error(f"Ignoring exception in command {ctx.command}:", exc_info=error)

        # We pass the error string to UI.error so it formats it in a code block
        await ctx.send(embed=UI.error("Unexpected Error", str(error)))


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))

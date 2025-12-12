import discord
from discord.ext import commands

from core.blacklist import blacklist_store
from core.config import settings


def is_owner():
    def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id != settings.OWNER_ID:
            raise commands.NotOwner("You are not the bot owner.")
        return True

    return commands.check(predicate)


def is_admin():
    def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id == settings.OWNER_ID:
            return True

        role = discord.utils.get(ctx.author.roles, name=settings.ADMIN_ROLE_NAME)
        if role is None:
            raise commands.MissingRole(settings.admin_role_name)

        return True

    return commands.check(predicate)


def not_blacklisted():
    async def predicate(ctx):
        if ctx.guild is None:
            return True

        cmd_name = ctx.command.name
        if blacklist_store.is_blocked(ctx.guild.id, ctx.author.id, cmd_name):
            raise commands.CheckFailure(f"User is blacklisted from {cmd_name}")
        return True

    return commands.check(predicate)


"""
def in_channel(allowed_channels: list[int]):
    def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id == settings.owner_id:
            return True

        if ctx.channel.id not in allowed_channels:
            raise commands.CheckFailure(f"Command not allowed in {ctx.channel.mention}")

        return True
    return commands.check(predicate)
"""

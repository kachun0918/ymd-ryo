"""
Alias feature cog.

Technical:
- Exposes alias CRUD commands and delegates persistence to core alias services.
- Integrates IAM checks for blacklist and owner/admin deletion permissions.

Plain language:
- Lets users create nickname shortcuts for members (e.g. `!9up myalias`).
- Makes repeated mentions/searches faster in chat commands.
"""

import discord
from discord.ext import commands

from core.alias import (
    add_alias_link,
    get_alias_adder,
    initialize,
    list_alias_links,
    remove_alias_link,
)
from core.config import settings
from core.iam import not_blacklisted
from core.ui import UI


class Alias(commands.Cog):
    """
    Member alias management commands.

    Plain language:
    - Create, remove, and list custom names for people in this server.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Ensure alias storage schema exists when cog is loaded."""
        await initialize()

    @commands.command(name="alias")
    @not_blacklisted()
    async def add_alias(self, ctx, target: discord.Member, alias_name: str):
        """Create an alias -> member link in the current guild."""
        clean_name = alias_name.lower()

        if clean_name in ["me", "bot", "all", "here", "everyone"]:
            return await ctx.send(embed=UI.warn("Invalid Alias", "That name is reserved."))

        if target.bot:
            return await ctx.send(
                embed=UI.warn("Invalid Target", "You cannot create an alias for a bot.")
            )

        success = await add_alias_link(ctx.guild.id, clean_name, target.id, ctx.author.id)
        if success:
            await ctx.send(
                embed=UI.success("Alias Added", f"Linked `{clean_name}` → **{target.display_name}**")
            )
        else:
            await ctx.send(
                embed=UI.warn(
                    "Already Exists",
                    f"**{target.display_name}** is already linked to `{clean_name}`.",
                )
            )

    @commands.command(name="unalias")
    @not_blacklisted()
    async def remove_alias(self, ctx, target: discord.Member, alias_name: str):
        """Delete an alias link if requester has permission."""
        clean_name = alias_name.lower()

        row = await get_alias_adder(ctx.guild.id, clean_name, target.id)
        if not row:
            return await ctx.send(embed=UI.warn("Not Found", "That alias link does not exist."))

        added_by_id = row[0]

        is_creator = ctx.author.id == added_by_id
        is_owner = ctx.author.id == settings.OWNER_ID
        admin_role_name = settings.ADMIN_ROLE_NAME
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
                    "Permission Denied", "Only the original creator or an Admin can delete this alias."
                )
            )

        await remove_alias_link(ctx.guild.id, clean_name, target.id)
        await ctx.send(
            embed=UI.success("Alias Removed", f"Unlinked `{clean_name}` from **{target.display_name}**")
        )

    @commands.command(name="listalias")
    @not_blacklisted()
    async def list_aliases(self, ctx, target: discord.Member):
        """
        List all aliases linked to one member.

        Plain language:
        - Shows every custom shortcut currently mapped to that user.
        """
        rows = await list_alias_links(ctx.guild.id, target.id)

        if not rows:
            return await ctx.send(embed=UI.info(f"Aliases for {target.display_name}", "None found."))

        alias_list = ", ".join([f"`{row[0]}`" for row in rows])
        await ctx.send(embed=UI.info(f"Aliases for {target.display_name}", alias_list))


async def setup(bot):
    await bot.add_cog(Alias(bot))

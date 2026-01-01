from typing import Optional

import discord
from discord.ext import commands

from core.iam import not_blacklisted
from core.ui import UI
from core.views import DeleteQuoteView, PaginationView

from .db import QuoteManager
from .helpers import is_saveable, send_mimic_message


class Quotes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = QuoteManager("db/quotes.db")

    async def cog_load(self):
        await self.db.initialize()

    # --- COMMAND: !save ---
    @commands.command(name="save")
    @not_blacklisted()
    async def save(self, ctx):
        if not ctx.message.reference:
            return await ctx.send(embed=UI.warn(f"Reply to a message with `{ctx.prefix}save`."))
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            return await ctx.send(embed=UI.error("Error", "Original message not found."))

        if not is_saveable(ref_msg):
            return await ctx.send(
                embed=UI.warn("Cannot save bots, webhooks, links, or empty messages.")
            )

        success = await self.db.add_quote(
            guild_id=ctx.guild.id,
            user_id=ref_msg.author.id,
            adder_id=ctx.author.id,
            content=ref_msg.content,
            channel_id=ref_msg.channel.id,
            timestamp=int(ref_msg.created_at.timestamp()),
        )

        if success:
            await ctx.send(
                embed=UI.success("Saved", f"Recorded quote from **{ref_msg.author.display_name}**.")
            )
        else:
            await ctx.send(
                embed=UI.warn(
                    f"I already have that quote saved for **{ref_msg.author.display_name}**!"
                )
            )

    # --- COMMAND: !9up or !9up @user ---
    @commands.command(name="9up")
    @not_blacklisted()
    async def get_quote(self, ctx, member: Optional[discord.Member] = None, *, flags: str = ""):
        row = await self.db.get_random_quote(ctx.guild.id, member.id if member else None)

        if not row:
            target = member.display_name if member else "this server"
            return await ctx.send(embed=UI.info("No Quotes", f"No records found for **{target}**."))

        # Unpack tuple (Order matches db.py get_random_quote)
        (qid, content, ts_str, ch_id, uid, adder_id, added_ts, uses) = row

        target_member = member or ctx.guild.get_member(uid)

        if not target_member:
            try:
                target_member = await ctx.guild.fetch_member(uid)
            except (discord.NotFound, discord.HTTPException):

                class DummyMember:
                    display_name = "Unknown User"
                    display_avatar = ctx.guild.icon or discord.Embed.Empty
                    color = discord.Color.default()

                target_member = DummyMember()

        footer_embed = None
        if "-f" in flags:
            adder_text = f"<@{adder_id}>" if adder_id else "System"
            added_date = f"<t:{added_ts}:R>" if added_ts else "Unknown"

            footer_embed = discord.Embed(color=target_member.color)
            footer_embed.add_field(
                name="📜 Context", value=f"<#{ch_id}>\n<t:{ts_str}:f>", inline=True
            )
            footer_embed.add_field(
                name="✍️ Added By", value=f"{adder_text}\n{added_date}", inline=True
            )
            footer_embed.add_field(
                name="📊 Stats", value=f"Used **{uses + 1}** times", inline=False
            )

        await send_mimic_message(ctx, target_member, content, footer_embed)

    # --- COMMAND: !9uplist @user ---
    @commands.command(name="9uplist")
    @not_blacklisted()
    async def list_quotes(self, ctx, member: discord.Member):
        if member.bot:
            return await ctx.send(embed=UI.warn("Bots do not have quotes."))

        rows = await self.db.get_quotes_for_list(ctx.guild.id, member.id)

        if not rows:
            return await ctx.send(
                embed=UI.info("Empty", f"No quotes found for **{member.display_name}**.")
            )

        view = PaginationView(rows, f"Quotes by {member.display_name}", member)
        embed = view.create_embed()
        await ctx.send(embed=embed, view=view)

    # --- COMMAND: !9uptop / !9uptop @user  ---
    @commands.command(name="9uptop")
    @not_blacklisted()
    async def top_quotes(self, ctx, member: Optional[discord.Member] = None):
        async with ctx.typing():
            rows = await self.db.get_top_quotes(ctx.guild.id, member.id if member else None)

            if not rows:
                msg = (
                    f"**{member.display_name}** has no highly used quotes."
                    if member
                    else "No quotes used yet."
                )
                return await ctx.send(embed=UI.info("No Data", msg))

            title_text = f"🏆 9up: {member.display_name}" if member else "🏆 9up Leaderboard"
            embed = discord.Embed(
                title=title_text, color=member.color if member else discord.Color.gold()
            )

            leaderboard_text = ""
            medals = ["🥇", "🥈", "🥉"]

            for index, (content, user_id, uses) in enumerate(rows):
                # Truncate content
                display_content = content.replace("\n", " ")
                if len(display_content) > 40:
                    display_content = display_content[:37] + "..."

                # Rank Emoji
                rank = medals[index] if index < 3 else f"`#{index + 1}`"

                if member:
                    leaderboard_text += f"{rank} 「{display_content}」 • **{uses}** uses\n\n"
                else:
                    leaderboard_text += (
                        f"{rank} 「{display_content}」\nby <@{user_id}> • **{uses}** uses\n\n"
                    )

            embed.description = leaderboard_text
            await ctx.send(embed=embed)

    # --- COMMAND: !9updel / !9updel @user ---
    @commands.command(name="9updel")
    @not_blacklisted()
    async def delete_quote_menu(self, ctx, member: discord.Member):
        rows = await self.db.get_quotes_for_deletion(ctx.guild.id, member.id)

        if not rows:
            return await ctx.send(
                embed=UI.info("Empty", f"No quotes found for **{member.display_name}**.")
            )

        view = DeleteQuoteView(
            rows, f"Delete Quote: {member.display_name}", member, ctx, self.db.db_path
        )
        embed = view.create_embed()

        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # ==========================================================================
    # ⚠️ ERROR HANDLING
    # ==========================================================================
    @get_quote.error
    async def get_quote_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=UI.warn(f"Please tag a user. Usage: `{ctx.prefix}9up @User`"))
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=UI.warn("I couldn't find that user."))


async def setup(bot):
    await bot.add_cog(Quotes(bot))

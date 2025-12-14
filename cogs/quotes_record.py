import logging
import os
from typing import Optional

import aiosqlite
import discord
from discord.ext import commands

from core.iam import not_blacklisted
from core.views import PaginationView

logger = logging.getLogger("discord.recorder")


class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/quotes.db"

    async def cog_load(self):
        if not os.path.exists("db"):
            os.makedirs("db")

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    user_id INTEGER,
                    content TEXT,
                    timestamp TEXT,
                    channel_id INTEGER,
                    adder_user_id INTEGER,
                    added_timestamp INTEGER,
                    uses INTEGER DEFAULT 0
                )
            """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_guild_user ON quotes(guild_id, user_id)"
            )
            await db.execute("CREATE INDEX IF NOT EXISTS idx_uses ON quotes(uses DESC)")
            await db.commit()

    # --- COMMAND: !save ---
    @commands.command(name="save")
    @not_blacklisted()
    async def save_quote(self, ctx):
        if not ctx.guild:
            return

        # Check if it is a Reply
        if not ctx.message.reference:
            await ctx.send(f"❌ Please reply to a message with `{ctx.prefix}save` to record it.")
            return

        # Fetch the message
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            await ctx.send("❌ Message not found (it might be deleted).")
            return

        # Ignore Bots
        if ref_msg.author.bot:
            await ctx.send("❌ I cannot save messages from bots.")
            return
        # Ignore Webhooks (MimicBot messages)
        if ref_msg.webhook_id is not None:
            await ctx.send("❌ I cannot save webhook messages.")
            return
        # Ignore Links
        if "http://" in ref_msg.content or "https://" in ref_msg.content:
            await ctx.send("❌ I cannot save messages containing links.")
            return
        # Ignore Empty
        if not ref_msg.content:
            await ctx.send("❌ Cannot save empty messages.")
            return

        orig_time = int(ref_msg.created_at.timestamp())
        orig_channel = ref_msg.channel.id

        # Check duplications
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id FROM quotes WHERE guild_id = ? AND user_id = ? AND content = ?
                """,
                (ctx.guild.id, ref_msg.author.id, ref_msg.content),
            )
            data = await cursor.fetchone()

            if data:
                await ctx.send(
                    f"""
                    ⚠️ I already have that quote saved for **{ref_msg.author.display_name}**!
                    """
                )
                return

            await db.execute(
                """
                INSERT INTO quotes (
                guild_id, user_id, content, timestamp,
                channel_id, adder_user_id, added_timestamp, uses)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    ctx.guild.id,
                    ref_msg.author.id,
                    ref_msg.content,
                    str(orig_time),
                    orig_channel,
                    ctx.author.id,
                    int(discord.utils.utcnow().timestamp()),
                ),
            )
            await db.commit()

        log_guildname = ctx.guild.name.replace("\n", " ")
        if len(log_guildname) > 15:
            log_guildname = log_guildname[:12] + "..."

        log_content = ref_msg.content.replace("\n", " ")
        if len(log_content) > 30:
            log_content = log_content[:27] + "..."

        logger.info(
            f"💾 Saved quote in '{log_guildname}', "
            f"Author: {ref_msg.author.display_name}, "
            f"Saved By: {ctx.author.display_name}, "
            f'Content: "{log_content}"'
        )
        await ctx.send(f'✅ Recorded: "{ref_msg.content}"')

    # --- COMMAND: 9up @user ---
    @commands.command(name="9up")
    @not_blacklisted()
    async def get_quote(self, ctx, member: Optional[discord.Member] = None, *, flags: str = ""):
        if not ctx.guild:
            return

        # Check if -f is included
        show_footer = "-f" in flags

        try:
            async with aiosqlite.connect(self.db_path) as db:
                if member:
                    query = """
                        SELECT id, content, timestamp, channel_id,
                            user_id, adder_user_id, added_timestamp, uses
                        FROM quotes
                        WHERE guild_id = ?
                        AND user_id = ?
                        AND content NOT LIKE '%http%'
                        ORDER BY RANDOM() LIMIT 1
                    """
                    params = (ctx.guild.id, member.id)
                else:
                    query = """
                        SELECT id, content, timestamp, channel_id,
                            user_id, adder_user_id, added_timestamp, uses
                        FROM quotes
                        WHERE guild_id = ?
                        AND content NOT LIKE '%http%'
                        ORDER BY RANDOM() LIMIT 1
                    """
                    params = (ctx.guild.id,)

                async with db.execute(query, params) as cursor:
                    row = await cursor.fetchone()

                if not row:
                    if member:
                        await ctx.send(f"📜 No clean records for **{member.display_name}**.")
                    else:
                        await ctx.send("📜 No valid quotes found in this server.")
                    return

                # Unpack new columns
                (
                    quote_id,
                    content,
                    timestamp_str,
                    channel_id,
                    author_id,
                    adder_id,
                    added_ts,
                    uses,
                ) = row

                # --- INCREMENT USAGE COUNT ---
                await db.execute("UPDATE quotes SET uses = uses + 1 WHERE id = ?", (quote_id,))
                await db.commit()

            # Resolve member if we are in "Random" mode
            if member is None:
                member = ctx.guild.get_member(author_id)
                if not member:
                    try:
                        member = await ctx.guild.fetch_member(author_id)
                    except discord.NotFound:

                        class DummyMember:
                            display_name = "Unknown User"
                            display_avatar = ctx.guild.icon or discord.Embed.Empty
                            color = discord.Color.default()
                            bot = False

                        member = DummyMember()

            # --- RUNTIME BOT CHECK ---
            if member.bot:
                await ctx.send("🤖 Cannot add bot message.")
                return

            mimic_name = f"🗣️ {member.display_name}"

            # --- FOOTER EMBED ---
            footer_embed = None

            if show_footer:
                current_uses = uses + 1

                adder_text = f"<@{adder_id}>" if adder_id else "System"
                added_date_text = f"<t:{added_ts}:R>" if added_ts else "Unknown date"

                footer_embed = discord.Embed(color=member.color)
                # Row 1: Original Context
                footer_embed.add_field(
                    name="📜 Original", value=f"<#{channel_id}>\n<t:{timestamp_str}:f>", inline=True
                )
                # Row 2: Adder Info
                footer_embed.add_field(
                    name="✍️ Added By", value=f"{adder_text}\n{added_date_text}", inline=True
                )
                # Row 3: Stats
                footer_embed.add_field(
                    name="📊 Popularity", value=f"Triggered **{current_uses}** times", inline=False
                )

            # --- WEBHOOK ---
            perms = ctx.channel.permissions_for(ctx.guild.me)
            if perms.manage_webhooks:
                try:
                    webhooks = await ctx.channel.webhooks()
                    webhook = discord.utils.get(webhooks, name="MimicBot")
                    if not webhook:
                        webhook = await ctx.channel.create_webhook(name="MimicBot")

                    await webhook.send(
                        content=content,
                        username=mimic_name,
                        avatar_url=member.display_avatar.url
                        if hasattr(member.display_avatar, "url")
                        else member.display_avatar,
                        allowed_mentions=discord.AllowedMentions.none(),
                        embed=footer_embed,
                    )
                    return
                except Exception as e:
                    logger.warning(f"Webhook failed: {e}. Falling back to Embed.")

            # --- Fallback to Embed ---
            main_embed = discord.Embed(description=content, color=member.color)
            main_embed.set_author(
                name=mimic_name,
                icon_url=member.display_avatar.url
                if hasattr(member.display_avatar, "url")
                else member.display_avatar,
            )

            # Merge footer fields into main embed if needed
            if show_footer and footer_embed:
                for field in footer_embed.fields:
                    main_embed.add_field(name=field.name, value=field.value, inline=field.inline)

            await ctx.send(embed=main_embed, allowed_mentions=discord.AllowedMentions.none())

        except Exception as e:
            logger.error(f"Database error during fetch: {e}")
            await ctx.send("❌ An internal database error occurred.")

    # --- COMMAND: !9uplist @user ---
    @commands.command(name="9uplist")
    @not_blacklisted()
    async def list_quotes(self, ctx, member: discord.Member):
        if not ctx.guild:
            return

        # 1. Inhibit Bot Tagging
        if member.bot:
            await ctx.send("🤖 Bots do not have quote records.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            # 2. Updated Query: Added 'uses' column
            query = """
                SELECT content, added_timestamp, adder_user_id, uses
                FROM quotes
                WHERE guild_id = ? AND user_id = ?
                ORDER BY added_timestamp DESC
            """
            async with db.execute(query, (ctx.guild.id, member.id)) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await ctx.send(f"📜 No recorded quotes found for **{member.display_name}**.")
            return

        view = PaginationView(rows, f"Quotes by {member.display_name}", member)
        embed = view.create_embed()
        await ctx.send(embed=embed, view=view)

    # --- ERROR HANDLER ---
    @get_quote.error
    async def get_quote_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"⚠️ Please tag a user. Usage: `{ctx.prefix}9up @User`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ I couldn't find that user. ")
        else:
            logger.error(f"Error in 9up: {error}")
            await ctx.send("❌ An error occurred.")


# Standard setup hook
async def setup(bot):
    await bot.add_cog(Recorder(bot))

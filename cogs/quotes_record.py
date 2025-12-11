import logging
import os
import random

import aiosqlite
import discord
from discord.ext import commands

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
                    channel_id INTEGER
                )
            """
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_guild_user ON quotes(guild_id, user_id)"
            )
            await db.commit()
        logger.info("Database connection established")

    # --- COMMAND: !save ---
    @commands.command(name="save")
    async def save_quote(self, ctx):
        if not ctx.guild:
            return

        # Check if it is a Reply
        if not ctx.message.reference:
            await ctx.send("❌ Please reply to a message with `!save` to record it.")
            return

        # Fetch the message
        try:
            ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        except discord.NotFound:
            await ctx.send("❌ Message not found (it might be deleted).")
            return

        # Check Content
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
                # If data != None, it means the quote exists
                await ctx.send(
                    f"""
                    ⚠️ I already have that quote saved for
                    ** {ref_msg.author.display_name}**!
                    """
                )
                return

            await db.execute(
                """
                INSERT INTO quotes (guild_id, user_id, content, timestamp, channel_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    ctx.guild.id,
                    ref_msg.author.id,
                    ref_msg.content,
                    str(orig_time),
                    orig_channel,
                ),
            )
            await db.commit()

        logger.info(
            f"💾 Saved quote in Guild {ctx.guild.id} from User {ref_msg.author.id}"
        )
        await ctx.send(f'✅ Recorded: "{ref_msg.content}"')

    # --- COMMAND: !9up @user ---
    @commands.command(name="9up")
    async def get_quote(self, ctx, member: discord.Member):
        if not ctx.guild:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT content, timestamp, channel_id
                    FROM quotes
                    WHERE guild_id = ? AND user_id = ?"
                """
                async with db.execute(query, (ctx.guild.id, member.id)) as cursor:
                    rows = await cursor.fetchall()

            if not rows:
                await ctx.send(f"📜 No records for **{member.display_name}**.")
                return

            # Pick random
            content, timestamp_str, channel_id = random.choice(rows)

            # Format the extra info
            # <t:123456:f>  : show "December 12, 2025 3:00 PM" in user's local time
            # <#123>        : creates a clickable link to the channel
            info_footer = f"\n\n*— <#{channel_id}> on <t:{timestamp_str}:f>*"

            # --- WEBHOOK ---
            # Checks if bot has permission to create webhooks
            perms = ctx.channel.permissions_for(ctx.guild.me)
            if perms.manage_webhooks:
                try:
                    webhooks = await ctx.channel.webhooks()
                    webhook = discord.utils.get(webhooks, name="MimicBot")
                    if not webhook:
                        webhook = await ctx.channel.create_webhook(name="MimicBot")

                    await webhook.send(
                        content=content + info_footer,
                        username=member.display_name,
                        avatar_url=member.display_avatar.url,
                    )
                    return
                except Exception as e:
                    logger.warning(f"Webhook failed: {e}. Falling back to Embed.")

            # --- fallback to embed if webhook failed ---
            embed = discord.Embed(description=content, color=member.color)
            embed.set_author(
                name=member.display_name, icon_url=member.display_avatar.url
            )
            embed.add_field(
                name="Context",
                value=f"<#{channel_id}>\n<t:{timestamp_str}:R>",
                inline=False,
            )
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Database error during fetch: {e}")
            await ctx.send("❌ An internal database error occurred.")

    # --- ERROR HANDLER ---
    @get_quote.error
    async def get_quote_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("⚠️ Please tag a user. Usage: `!9up @User`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("⚠️ I couldn't find that user. ")
        else:
            logger.error(f"Error in !9up: {error}")
            await ctx.send("❌ An error occurred.")


# Standard setup hook
async def setup(bot):
    await bot.add_cog(Recorder(bot))

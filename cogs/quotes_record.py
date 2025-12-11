import discord
from discord.ext import commands
import aiosqlite
import random
import os
import logging

logger = logging.getLogger('discord')

class Recorder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "db/quotes.db" 

    async def cog_load(self):
        if not os.path.exists('db'):
            os.makedirs('db')
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
            """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT
                )
            """)
            await db.commit()
        logger.info("   └── [Recorder] Database connection established")

    # !save 
    @commands.command(name="save")
    async def save_quote(self, ctx):
        if not ctx.message.reference:
            await ctx.send("Please reply to a message with `!9save` to record it.")
            return

        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        
        if not ref_msg.content:
            await ctx.send("I can't save empty messages.")
            return

        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO quotes (user_id, content) VALUES (?, ?)",
                (ref_msg.author.id, ref_msg.content)
            )
            await db.commit()

        await ctx.send(f"✅ Recorded: \"{ref_msg.content}\"")

    # !9up @User 
    @commands.command(name="9up")
    async def get_quote(self, ctx, member: discord.Member):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute("SELECT content FROM quotes WHERE user_id = ?", (member.id,)) as cursor:
                rows = await cursor.fetchall()

        if rows:
            random_quote = random.choice(rows)[0]
            await ctx.send(f"🗣️ {member.mention} once said: \"{random_quote}\"")
        else:
            await ctx.send(f"I don't have any records for {member.display_name}.")

# Standard setup hook
async def setup(bot):
    await bot.add_cog(Recorder(bot))
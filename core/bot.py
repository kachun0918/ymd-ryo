import discord
from discord.ext import commands
from .logger import setup_logging

# Logger
setup_logging()

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Instantiate
bot = commands.Bot(command_prefix="!", intents=intents)

# 4. Define Standard Events
@bot.event
async def on_ready():
    import logging
    logger = logging.getLogger('discord')
    logger.info("---------------------------------------------")
    logger.info(f"👤 Logged in as: {bot.user.name}")
    logger.info(f"🆔 ID: {bot.user.id}")
    logger.info("---------------------------------------------")
import discord
import logging
from discord.ext import commands
from .logger import setup_logging

# Logger
setup_logging()
logger = logging.getLogger('discord')

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Instantiate
bot = commands.Bot(command_prefix="!", intents=intents)

# 4. Define Standard Events
@bot.event
async def on_ready():
    logger.info("---------------------------------------------")
    logger.info(f"👤 Logged in as: {bot.user.name}")
    logger.info(f"🆔 ID: {bot.user.id}")
    logger.info("---------------------------------------------")
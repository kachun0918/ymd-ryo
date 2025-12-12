import discord
from discord.ext import commands

from core.server_settings import server_settings

from .logger import setup_logging

# Logger
setup_logging()

# Intents
intents = discord.Intents.default()
intents.message_content = True


# Instantiate
def get_prefix(bot, message):
    if not message.guild:
        return "!"

    return server_settings.get_prefix(message.guild.id)


bot = commands.Bot(command_prefix=get_prefix, intents=intents)


# Define Standard Events
@bot.event
async def on_ready():
    import logging

    logger = logging.getLogger("discord")
    logger.info("---------------------------------------------")
    logger.info(f"👤 Logged in as: {bot.user.name}")
    logger.info(f"🆔 ID: {bot.user.id}")
    logger.info("---------------------------------------------")

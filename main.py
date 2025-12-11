import asyncio
import logging
from core.logger import setup_logging
from core.config import settings
from core.bot import bot
from core.loader import load_cogs

setup_logging()
logger = logging.getLogger('discord.bot')

async def main():
    logger.info("📢 Bot started")
    async with bot:
        await load_cogs(bot)
        logger.info("🔑 Authenticating...")
        await bot.start(settings.BOT_TOKEN.get_secret_value())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user.")
        pass
    except Exception as e:
        logger.critical(f"❌ Critical Error: {e}", exc_info=True)
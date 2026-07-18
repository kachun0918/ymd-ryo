import asyncio
import logging

from core.bot import bot
from core.config import settings
from core.loader import load_cogs
from core.logger import setup_logging

setup_logging()
logger = logging.getLogger("discord.bot")


async def main():
    logger.info("📢 Bot started")
    async with bot:
        try:
            await bot.load_extension("core.error_handler")
            logger.info("🛡️ Core error handler loaded.")
        except Exception as e:
            logger.critical(f"❌ Failed to load core.error_handler: {e}", exc_info=True)
            raise RuntimeError("Failed to load core.error_handler") from e
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

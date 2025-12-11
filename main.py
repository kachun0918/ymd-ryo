import asyncio
import logging
from core.config import settings
from core.bot import bot
from core.loader import load_cogs  

logger = logging.getLogger('discord')

async def main():
    async with bot:
        await load_cogs(bot)
        await bot.start(settings.BOT_TOKEN.get_secret_value())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.critical(f"❌ Critical Error: {e}", exc_info=True)
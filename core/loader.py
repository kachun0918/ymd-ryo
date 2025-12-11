"""
    Scans the 'cogs' directory and loads all extensions.
"""
import os
import logging

logger = logging.getLogger('discord')

async def load_cogs(bot):
    if not os.path.exists('cogs'):
        logger.warning("No 'cogs' directory found.")
        return

    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            extension_name = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(extension_name)
                logger.info(f"📦 Loaded extension: {filename}")
            except Exception as e:
                logger.error(f"❌ Failed to load {filename}: {e}", exc_info=True)
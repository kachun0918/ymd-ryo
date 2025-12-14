import logging
import os

logger = logging.getLogger("discord")


async def load_cogs(bot):
    if not os.path.exists("cogs"):
        logger.warning("No 'cogs' directory found.")
        return

    for root, dirs, files in os.walk("./cogs"):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                relative_path = os.path.relpath(root, ".")
                module_path = relative_path.replace(os.path.sep, ".")
                extension_name = f"{module_path}.{filename[:-3]}"

                try:
                    await bot.load_extension(extension_name)
                    logger.info(f"📦 Loaded extension: {extension_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load {extension_name}: {e}", exc_info=True)

import logging
import os

from discord.ext import commands

logger = logging.getLogger("discord")


IGNORE_FILES = {"db.py", "helpers.py", "helper.py", "views.py", "ui.py", "config.py", "cog.py"}


async def load_cogs(bot):
    if not os.path.exists("cogs"):
        logger.warning("No 'cogs' directory found.")
        return

    for root, dirs, files in os.walk("./cogs"):
        if any(part.startswith("_") for part in root.split(os.sep)):
            continue

        for filename in files:
            if not filename.endswith(".py"):
                continue
            if filename in IGNORE_FILES:
                continue
            if filename.startswith("_"):
                continue

            # Calculate path: cogs/features/quotes/cog.py -> cogs.features.quotes.cog
            relative_path = os.path.relpath(root, ".")
            module_path = relative_path.replace(os.path.sep, ".")
            extension_name = f"{module_path}.{filename[:-3]}"

            try:
                await bot.load_extension(extension_name)
                logger.info(f"📦 Loaded extension: {extension_name}")

            except commands.NoEntryPointError:
                logger.debug(f"ℹ️ Skipped {extension_name} (No setup function found)")

            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"⚠️ {extension_name} is already loaded.")

            except Exception as e:
                logger.error(f"❌ Failed to load {extension_name}: {e}", exc_info=True)

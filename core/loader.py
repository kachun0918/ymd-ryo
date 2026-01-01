import logging
import os

from discord.ext import commands

logger = logging.getLogger("discord")

IGNORE_FILES = {
    "__init__.py",
    "db.py",
    "helpers.py",
    "views.py",
    "ui.py",
    "config.py",
    "capture.py",
    "cog.py",
}


async def load_cogs(bot):
    if not os.path.exists("cogs"):
        logger.warning("No 'cogs' directory found.")
        return

    for root, dirs, files in os.walk("./cogs"):
        # Skip private folders (e.g. __pycache__)
        if any(part.startswith("_") for part in root.split(os.sep)):
            continue

        if "__init__.py" in files and "cog.py" in files:
            relative_path = os.path.relpath(root, ".")
            module_path = relative_path.replace(os.path.sep, ".")

            try:
                await bot.load_extension(module_path)
                logger.info(f"📦 Loaded extension package: {module_path}")
            except Exception as e:
                logger.error(f"❌ Failed to load package {module_path}: {e}", exc_info=True)

            # 🛑 STOP here for this folder.
            # We already loaded the package, so don't try to load 'cog.py' or 'capture.py' individually.
            continue

        for filename in files:
            if not filename.endswith(".py"):
                continue

            if filename in IGNORE_FILES:
                continue

            if filename.startswith("_"):
                continue

            relative_path = os.path.relpath(root, ".")
            module_path = relative_path.replace(os.path.sep, ".")
            extension_name = f"{module_path}.{filename[:-3]}"

            try:
                await bot.load_extension(extension_name)
                logger.info(f"📦 Loaded extension: {extension_name}")
            except commands.NoEntryPointError:
                pass
            except commands.ExtensionAlreadyLoaded:
                logger.warning(f"⚠️ {extension_name} is already loaded.")
            except Exception as e:
                logger.error(f"❌ Failed to load {extension_name}: {e}", exc_info=True)

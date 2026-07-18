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


def _is_private_path(path: str) -> bool:
    return any(part.startswith("_") for part in path.split(os.sep))


async def _load_extension_safe(bot, extension_name: str, is_package: bool = False):
    try:
        await bot.load_extension(extension_name)
        if is_package:
            logger.info(f"📦 Loaded extension package: {extension_name}")
        else:
            logger.info(f"📦 Loaded extension: {extension_name}")
    except commands.NoEntryPointError:
        pass
    except commands.ExtensionAlreadyLoaded:
        logger.warning(f"⚠️ {extension_name} is already loaded.")
    except Exception as e:
        kind = "package" if is_package else "extension"
        logger.error(f"❌ Failed to load {kind} {extension_name}: {e}", exc_info=True)


async def load_cogs(bot):
    if not os.path.exists("cogs"):
        logger.warning("No 'cogs' directory found.")
        return

    for root, dirs, files in os.walk("./cogs"):
        # Deterministic load order for stable startup behavior.
        dirs.sort()
        files.sort()

        # Skip private folders (e.g. __pycache__).
        if _is_private_path(root):
            continue

        if "__init__.py" in files and "cog.py" in files:
            relative_path = os.path.relpath(root, ".")
            module_path = relative_path.replace(os.path.sep, ".")
            await _load_extension_safe(bot, module_path, is_package=True)

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

            await _load_extension_safe(bot, extension_name)

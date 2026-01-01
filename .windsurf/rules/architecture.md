# Project: Modular Discord Bot (Python/Nextcord/Discord.py)

## High-Level Context
This is an asynchronous Discord bot built with `discord.py`. It features a strict separation between "Infrastructure" (Core) and "Features" (Cogs).
- **Owner:** The user is the bot owner.
- **Environment:** Python 3.10+, `aiosqlite` for DB, `pydantic` for config.

## Core Directives
1. **Always Async:** Never use blocking IO (time.sleep, requests, synchronous file open). Use `asyncio` and `aiosqlite`.
2. **Modular Cogs:** All features must go into `cogs/` and be reloadable.
3. **Dynamic Context:** Never hardcode prefixes (`!`). Use `{ctx.prefix}`.
4. **Silent Fail:** Public commands must fail silently for unauthorized users.

## References
For specific implementation details, refer to:
- `.windsurf/architecture.md` (Folder structure & core logic)
- `.windsurf/coding_style.md` (Snippets & typing)
- `.windsurf/bot_patterns.md` (IAM, Security, Data)
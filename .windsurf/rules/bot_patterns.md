# Bot Implementation Patterns

## 1. Dynamic Prefixes
Never assume the prefix is `!`. It varies per guild.
- **In Messages:** Use `f"Usage: {ctx.prefix}command"`
- **In Code:** Use `ctx.prefix` variable.

## 2. Security (IAM)
All commands must have a security decorator unless they are purely public info.
- **Admin Only:**
    ```python
    from core.iam import is_owner
    @is_owner()
    ```

- **Public Protection:**
    ```python
    from core.iam import not_blacklisted
    @not_blacklisted()
    ```

## 3. Error Handling
Local Handlers: Avoid try/except blocks for command checks inside the command itself. Let errors bubble up.

Global Handler: cogs/errorhandler.py catches all.

## 4. Standard Cog Template
Use this template for all new files in cogs/:
Silence: CheckFailure, NotOwner, and MissingRole must be ignored (return None) to prevent spamming users who don't have access.

import discord
import logging
from discord.ext import commands
from core.iam import not_blacklisted

logger = logging.getLogger("bot.cogs.feature_name")

class FeatureName(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command()
    @not_blacklisted()
    async def hello(self, ctx):
        await ctx.send(f"Hello! Your prefix is `{ctx.prefix}`")

async def setup(bot):
    await bot.add_cog(FeatureName(bot))
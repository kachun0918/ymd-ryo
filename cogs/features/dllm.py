import discord
from discord.ext import commands
import json
import random
import os
import logging

logger = logging.getLogger("bot.dllm")

class dllm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.links_file = "data/dllm_links.json"
        self.links = []
        self._load_links()

    def _load_links(self):
        if os.path.exists(self.links_file):
            try:
                with open(self.links_file, "r") as f:
                    self.links = json.load(f)
                logger.info(f"✅ Loaded {len(self.links)} DLLM assets.")
            except Exception as e:
                logger.error(f"❌ Failed to load DLLM links: {e}")
                self.links = []
        else:
            logger.warning(f"⚠️ DLLM file not found at {self.links_file}")
            self.links = []

    async def _get_webhook(self, ctx):
        is_thread = isinstance(ctx.channel, discord.Thread)
        channel = ctx.channel.parent if is_thread else ctx.channel

        webhooks = await channel.webhooks()
        webhook = next((w for w in webhooks if w.user == self.bot.user), None)

        if not webhook:
            webhook = await channel.create_webhook(name="Yamada Proxy")

        return webhook, is_thread

    @commands.command(aliases=["sticker", "gif"])
    async def dllm(self, ctx):
        
        if not self.links:
            return await ctx.send("❌ No assets loaded!")

        sticker_url = random.choice(self.links)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass  # If we can't delete, just move on

        if ctx.channel.permissions_for(ctx.guild.me).manage_webhooks:
            try:
                webhook, is_thread = await self._get_webhook(ctx)
                
                await webhook.send(
                    content=sticker_url,
                    username=ctx.author.display_name,
                    avatar_url=ctx.author.display_avatar.url,
                    thread=ctx.channel if is_thread else discord.utils.MISSING
                )
                return 
            except Exception as e:
                logger.error(f"Webhook impersonation failed: {e}")

        # Fallback (Normal Bot Message)
        await ctx.send(sticker_url)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload_dllm(self, ctx):
        self._load_links()
        await ctx.send(f"🔄 Reloaded! Total assets: **{len(self.links)}**")

async def setup(bot):
    await bot.add_cog(dllm(bot))
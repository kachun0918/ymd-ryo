import asyncio
import os
import random

import discord
from discord.ext import commands

from core.capture import Capture
from core.iam import not_blacklisted


class CCTV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor = Capture("https://www.youtube.com/@SilvercordTST/streams")

    @commands.command()
    @not_blacklisted()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.guild, wait=True)
    async def cctv(self, ctx, game: str, side: str = None):
        """
        Usage: !cctv <game> [side]
        Example: !cctv sdvx L  |  !cctv sdvx
        """
        game = game.lower()

        if game == "iidx":
            embed = discord.Embed(
                title="🎹 Beatmania IIDX",
                description="🚧 **Deployment in progress.**",
                color=discord.Color.gold(),
            )
            return await ctx.send(embed=embed)

        elif game == "sdvx":
            if side is None:
                side = random.choice(["L", "R"])
            side = side.upper()
            if side not in ["L", "R"]:
                return await ctx.send("❌ Invalid side! Use **L** or **R**.")

            status_msg = await ctx.send(f"🔍 Searching live: **SDVX - {side}** ...")

            loop = asyncio.get_event_loop()

            # Get URL
            stream_data = await loop.run_in_executor(None, self.monitor.get_stream_info, game, side)
            if not stream_data:
                await status_msg.delete()
                return await ctx.send(
                    f"⚠️ **Stream Offline**\nCould not find a live stream for SDVX {side}."
                )

            url = stream_data["url"]
            title = stream_data["title"]

            # Capture
            filename = f"cctv_{game}_{side}.jpg"
            file_path = await loop.run_in_executor(None, self.monitor.capture_frame, url, filename)

            await status_msg.delete()

            if file_path and os.path.exists(file_path):
                # 3. Upload
                file = discord.File(file_path, filename=filename)
                embed = discord.Embed(
                    title=f"🔴 {title}",
                    url=url,
                    color=discord.Color.from_rgb(255, 0, 255)
                    if side == "R"
                    else discord.Color.blue(),
                )
                embed.set_image(url=f"attachment://{filename}")
                embed.set_footer(text=f"Requested by {ctx.author.display_name}")
                await ctx.send(file=file, embed=embed)
            else:
                await ctx.send("❌ Error: Failed to capture frame from the stream.")

        else:
            await ctx.send(f"❓ Unknown game `{game}`. Supported games: `sdvx`, `iidx`")


async def setup(bot):
    await bot.add_cog(CCTV(bot))

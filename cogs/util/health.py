import os
import platform
import time
from datetime import datetime, timedelta

import discord
import psutil
from discord.ext import commands

from core.iam import is_owner


class Health(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def _get_uptime(self):
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)
        return str(timedelta(seconds=uptime_seconds))

    # --- COMMAND: !reload ---
    @commands.command(hidden=True)
    @is_owner()
    async def health(self, ctx):
        """Displays system status."""
        async with ctx.typing():
            process = psutil.Process(os.getpid())
            ram_usage = process.memory_info().rss / 1024 / 1024
            cpu_usage = psutil.cpu_percent(interval=None)
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            embed = discord.Embed(
                title="🏥 System Health Check",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            embed.add_field(
                name="🏓 Latency", value=f"`{round(self.bot.latency * 1000)}ms`", inline=True
            )
            embed.add_field(name="⏱️ Uptime", value=f"`{self._get_uptime()}`", inline=True)
            embed.add_field(name="💻 OS", value=f"`{platform.system()} (Docker)`", inline=True)

            embed.add_field(name="🧠 RAM Usage", value=f"`{ram_usage:.2f} MB`", inline=True)
            embed.add_field(name="⚙️ CPU Load", value=f"`{cpu_usage}%`", inline=True)
            embed.add_field(name="Cw Disk Usage", value=f"`{disk_percent}%`", inline=True)

            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Health(bot))

import asyncio
import os
import random
from typing import Optional

import discord
from discord.ext import commands

from core.iam import not_blacklisted
from core.ui import UI

from .capture import Capture

GAME_CONFIG = {
    "sdvx": {
        "name": "SDVX",
        "sides": ["L", "R"],
        "color_l": discord.Color.blue(),
        "color_r": discord.Color.magenta(),
        "active": True,
    },
    "iidx": {
        "name": "Beatmania IIDX",
        "sides": [],
        "color": discord.Color.gold(),
        "active": False,  # Set to True when ready
    },
}


class CCTV(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monitor = Capture("https://www.youtube.com/@SilvercordTST/streams")

    # ==========================================================================
    # 🎮 COMMAND ENTRY POINT
    # ==========================================================================
    @commands.command()
    @not_blacklisted()
    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.max_concurrency(1, per=commands.BucketType.guild, wait=True)
    async def cctv(self, ctx, game: str, side: Optional[str] = None):
        """
        Usage: !cctv <game> [side]
        """
        game_key = game.lower()

        # 1. Validate Game
        if game_key not in GAME_CONFIG:
            supported = ", ".join(f"`{g}`" for g in GAME_CONFIG.keys())
            return await ctx.send(embed=UI.warn(f"Unknown game `{game}`. Supported: {supported}"))

        config = GAME_CONFIG[game_key]

        # 2. Check Active Status
        if not config["active"]:
            return await ctx.send(
                embed=UI.info(f"🎹 {config['name']}", "🚧 **Deployment in progress.**")
            )

        # 3. Validate/Resolve Side
        target_side = self._resolve_side(config, side)
        if target_side is False:  # Explicit check for False (invalid input)
            return await ctx.send(embed=UI.warn("Invalid side! Use **L** or **R**."))

        # 4. Execute Process
        await self._process_capture(ctx, game_key, target_side, config)

    # ==========================================================================
    # 🧩 HELPERS
    # ==========================================================================
    def _resolve_side(self, config: dict, side: Optional[str]):
        """
        Determines the side (L/R). Returns False if invalid, None if not applicable.
        """
        if not config["sides"]:
            return None  # Game doesn't have sides

        if side is None:
            return random.choice(config["sides"])

        side = side.upper()
        if side not in config["sides"]:
            return False

        return side

    async def _process_capture(self, ctx, game_key: str, side: str, config: dict):
        """
        Handles the heavy lifting: Searching, Capturing, and Sending.
        """
        # 1. UI Feedback
        side_text = f" - {side}" if side else ""
        status_msg = await ctx.send(f"🔍 Searching live: **{config['name']}{side_text}** ...")

        try:
            # 2. Get Stream URL (Run in thread to avoid blocking)
            # We use asyncio.to_thread which is cleaner than run_in_executor
            stream_data = await asyncio.to_thread(self.monitor.get_stream_info, game_key, side)

            if not stream_data:
                await status_msg.delete()
                await ctx.send(
                    embed=UI.error(
                        "Stream Offline",
                        f"Could not find a live stream for {config['name']}{side_text}.",
                    )
                )
                return

            # 3. Capture Frame
            filename = f"cctv_{game_key}_{side or 'main'}.jpg"
            file_path = await asyncio.to_thread(
                self.monitor.capture_frame, stream_data["url"], filename
            )

            # 4. Clean up status
            await status_msg.delete()

            # 5. Upload Result
            if file_path and os.path.exists(file_path):
                await self._send_capture_embed(ctx, file_path, filename, stream_data, side, config)
            else:
                await ctx.send(
                    embed=UI.error("Capture Failed", "Failed to capture frame from the stream.")
                )

        except Exception as e:
            # Cleanup if something crashed
            try:
                await status_msg.delete()
            except:
                pass
            await ctx.send(embed=UI.error("System Error", str(e)))

    async def _send_capture_embed(self, ctx, file_path, filename, stream_data, side, config):
        """Constructs and sends the final image embed."""

        # Determine Color
        if side == "R":
            color = config.get("color_r", discord.Color.default())
        elif side == "L":
            color = config.get("color_l", discord.Color.default())
        else:
            color = config.get("color", discord.Color.default())

        file = discord.File(file_path, filename=filename)

        embed = discord.Embed(
            title=f"🔴 {stream_data['title']}", url=stream_data["url"], color=color
        )
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.send(file=file, embed=embed)


async def setup(bot):
    await bot.add_cog(CCTV(bot))

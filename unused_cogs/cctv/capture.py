import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

from yt_dlp import YoutubeDL

logger = logging.getLogger("core.capture")


class Capture:
    def __init__(
        self,
        channel_url: str,
        cache_file: str = "data/stream_links_cache.json",
        img_dir: str = "data/img",
    ):
        self.channel_url = channel_url
        self.cache_file = Path(cache_file)
        self.img_dir = Path(img_dir)
        self.cache_ttl = 3600
        self.cookie_file = Path("/app/data/cookies.txt")

        # Ensure directories exist
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.img_dir.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # 💾 CACHE MANAGEMENT
    # ==========================================================================
    def _load_cache(self) -> Dict:
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_cache(self, data: Dict):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    # ==========================================================================
    # 🔍 SEARCH
    # ==========================================================================
    def get_stream_info(self, game: str, side: str) -> Optional[Dict]:
        """
        Synchronous wrapper if needed,
        but usage inside Cogs should use async wrapper via to_thread.
        """
        game, side = game.lower(), side.upper()
        cache = self._load_cache()
        current_time = time.time()

        # 1. Check Cache
        cached_entry = cache.get(game, {}).get(side)
        if cached_entry and "title" in cached_entry:
            if current_time - cached_entry.get("timestamp", 0) < self.cache_ttl:
                logger.debug(f"🚀 Found cached URL for {game} {side}")
                return cached_entry

        result = self._search_youtube_live(game, side)

        if result:
            url, title = result
            if game not in cache:
                cache[game] = {}

            cache[game][side] = {"url": url, "title": title, "timestamp": current_time}
            self._save_cache(cache)
            return cache[game][side]

        return None

    def _search_youtube_live(self, game: str, side: str):
        target_tag = (
            f"[SILVERCORD - {side}]" if game == "sdvx" else f"[SILVERCORD - {game.upper()}]"
        )
        logger.info(f"🔍 Scanning YouTube for: '{target_tag}'...")

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--match-filter",
            "is_live",
            "--print",
            "%(id)s::::%(title)s",
            self.channel_url,
        ]

        if self.cookie_file.exists():
            cmd.insert(1, f"--cookies={self.cookie_file}")

        try:
            # Run synchronously (since this is called inside to_thread in cog)
            import subprocess

            output = subprocess.check_output(cmd).decode("utf-8").strip()

            if not output:
                return None

            for line in output.split("\n"):
                if "::::" in line:
                    vid, title = line.split("::::", 1)
                    if target_tag in title:
                        return (f"https://www.youtube.com/watch?v={vid}", title)
            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"yt-dlp search failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None

    # ==========================================================================
    # 📸 CAPTURE
    # ==========================================================================
    def capture_frame(self, video_url: str, filename: str) -> Optional[str]:
        full_path = self.img_dir / filename

        if full_path.exists():
            if time.time() - full_path.stat().st_mtime < 30:
                logger.debug(f"⏩ Reusing fresh image: {filename}")
                return str(full_path)

        ydl_opts = {
            "format": "best",
            "quiet": True,
            "noplaylist": True,
        }
        if self.cookie_file.exists():
            ydl_opts["cookiefile"] = str(self.cookie_file)

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                direct_url = info.get("url")

            # 3. Capture with FFmpeg
            import subprocess

            cmd = ["ffmpeg", "-y", "-i", direct_url, "-vframes", "1", "-q:v", "2", str(full_path)]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return str(full_path)

        except Exception as e:
            logger.error(f"Capture failed: {e}")
            return None

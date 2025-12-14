import json
import logging
import os
import subprocess
import time

from yt_dlp import YoutubeDL

logger = logging.getLogger("discord.recorder")


class Capture:
    def __init__(self, channel_url, cache_file="data/stream_links_cache.json", img_dir="data/img"):
        self.channel_url = channel_url
        self.cache_file = cache_file
        self.img_dir = img_dir
        self.cache_ttl = 3600

        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        os.makedirs(self.img_dir, exist_ok=True)

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_cache(self, data):
        try:
            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=4)
        except IOError:
            pass

    def get_stream_info(self, game, side):
        """Returns {'url': '...', 'title': '...'} or None"""
        cache = self._load_cache()
        current_time = time.time()
        game, side = game.lower(), side.upper()

        # Check URL Cache
        cached_entry = cache.get(game, {}).get(side)
        if cached_entry and "title" in cached_entry:
            if current_time - cached_entry.get("timestamp", 0) < self.cache_ttl:
                logger.info(f"🚀 [Cache] Found URL for {game.upper()} {side}")
                return cached_entry

        # Search YouTube
        result = self._search_youtube_live(game, side)

        # Update Cache
        if result:
            url, title = result
            if game not in cache:
                cache[game] = {}

            cache[game][side] = {"url": url, "title": title, "timestamp": current_time}
            self._save_cache(cache)
            return cache[game][side]

        return None

    def _search_youtube_live(self, game, side):
        if game == "sdvx":
            target_tag = f"[SILVERCORD - {side}]"
        else:
            target_tag = f"[SILVERCORD - {game.upper()}]"

        logger.info(f"🔍 [Search] Scanning YouTube for: '{target_tag}'...")
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--match-filter",
            "is_live",
            "--print",
            "%(id)s::::%(title)s",
            self.channel_url,
        ]
        try:
            result = subprocess.check_output(cmd).decode("utf-8").strip()
            if not result:
                return None
            for line in result.split("\n"):
                if "::::" in line:
                    vid, title = line.split("::::", 1)
                    if target_tag in title:
                        return (f"https://www.youtube.com/watch?v={vid}", title)
            return None
        except Exception:
            return None

    def capture_frame(self, video_url, filename):
        """
        Captures a frame or reuses existing one if < 30s old.
        Returns the FULL PATH to the image on success, or None.
        """
        # 📂 path: data/img/cctv_sdvx_*.jpg
        full_path = os.path.join(self.img_dir, filename)

        # Check Image Cache
        if os.path.exists(full_path):
            last_modified = os.path.getmtime(full_path)
            if time.time() - last_modified < 15:
                logger.info(f"⏩ [Img Cache] Reusing fresh image: {filename}")
                return full_path

        # Capture New Image
        ydl_opts = {"format": "best", "quiet": True, "noplaylist": True}
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                direct_url = info.get("url")

            cmd = ["ffmpeg", "-y", "-i", direct_url, "-vframes", "1", "-q:v", "2", full_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            logger.info(f"📸 [Capture] Saved new image to {full_path}")
            return full_path
        except Exception as e:
            logger.info(f"❌ [Error] Capture failed: {e}")
            return None

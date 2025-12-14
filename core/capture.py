import json
import os
import subprocess
import time

from yt_dlp import YoutubeDL


class Capture:
    def __init__(self, channel_url, cache_file="data/stream_links_cache.json", img_dir="data/img"):
        self.channel_url = channel_url
        self.cache_file = cache_file
        self.img_dir = img_dir
        self.cache_ttl = 3600
        self.cookie_file = "/app/data/cookies.txt"  # Cookie: bypass youtube check

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
        cache = self._load_cache()
        current_time = time.time()
        game, side = game.lower(), side.upper()

        cached_entry = cache.get(game, {}).get(side)
        if cached_entry and "title" in cached_entry:
            if current_time - cached_entry.get("timestamp", 0) < self.cache_ttl:
                print(f"🚀 [Cache] Found URL for {game.upper()} {side}")
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

    def _search_youtube_live(self, game, side):
        if game == "sdvx":
            target_tag = f"[SILVERCORD - {side}]"
        else:
            target_tag = f"[SILVERCORD - {game.upper()}]"

        print(f"🔍 [Search] Scanning YouTube for: '{target_tag}'...")

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--match-filter",
            "is_live",
            "--print",
            "%(id)s::::%(title)s",
            self.channel_url,
        ]

        # Only add cookie flag if file exists
        if os.path.exists(self.cookie_file):
            cmd.insert(1, f"--cookies={self.cookie_file}")

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
        except Exception as e:
            print(f"❌ [Search Error] {e}")
            return None

    def capture_frame(self, video_url, filename):
        full_path = os.path.join(self.img_dir, filename)

        if os.path.exists(full_path):
            last_modified = os.path.getmtime(full_path)
            if time.time() - last_modified < 30:
                print(f"⏩ [Img Cache] Reusing fresh image: {filename}")
                return full_path

        ydl_opts = {"format": "best", "quiet": True, "noplaylist": True}

        if os.path.exists(self.cookie_file):
            ydl_opts["cookiefile"] = self.cookie_file

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                direct_url = info.get("url")

            cmd = ["ffmpeg", "-y", "-i", direct_url, "-vframes", "1", "-q:v", "2", full_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return full_path
        except Exception as e:
            print(f"❌ [Capture Error] {e}")
            return None

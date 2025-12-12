import json
import os
import logging

logger = logging.getLogger("core.settings")

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "server_settings.json")

# Default values for any new server
DEFAULT_SETTINGS = {
    "prefix": "!",
}


class ServerSettingsManager:
    def __init__(self):
        self._ensure_dir()
        self.data = self._load()

    def _ensure_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _load(self):
        if not os.path.exists(SETTINGS_FILE):
            return {}
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error(
                "Failed to load server settings. Starting with empty defaults."
            )
            return {}

    def _save(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_val(self, guild_id: int, key: str):
        """
        Generic getter for any setting.
        Returns the saved value OR the default value if not set.
        """
        gid = str(guild_id)

        # 1. Check if guild exists in data
        if gid not in self.data:
            return DEFAULT_SETTINGS.get(key)

        # 2. Check if specific key exists for that guild
        return self.data[gid].get(key, DEFAULT_SETTINGS.get(key))

    def set_val(self, guild_id: int, key: str, value):
        """Generic setter for any setting."""
        gid = str(guild_id)

        if gid not in self.data:
            self.data[gid] = {}

        self.data[gid][key] = value
        self._save()

    # --- Convenience Wrappers (Optional but clean) ---
    def get_prefix(self, guild_id: int) -> str:
        return self.get_val(guild_id, "prefix")


server_settings = ServerSettingsManager()

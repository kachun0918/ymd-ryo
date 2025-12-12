import json
import os

DATA_DIR = "data"
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")


class BlacklistManager:
    def __init__(self):
        self._ensure_dir()
        self.data = self._load()

    def _ensure_dir(self):
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _load(self):
        if not os.path.exists(BLACKLIST_FILE):
            return {}
        try:
            with open(BLACKLIST_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save(self):
        with open(BLACKLIST_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def add_block(self, guild_id: int, user_id: int, command_name: str):
        gid = str(guild_id)
        uid = str(user_id)

        # 1. Initialize Guild if missing
        if gid not in self.data:
            self.data[gid] = {}

        # 2. Initialize User if missing in that Guild
        if uid not in self.data[gid]:
            self.data[gid][uid] = []

        # 3. Add Command
        if command_name not in self.data[gid][uid]:
            self.data[gid][uid].append(command_name)
            self._save()
            return True
        return False

    def remove_block(self, guild_id: int, user_id: int, command_name: str):
        gid = str(guild_id)
        uid = str(user_id)

        # Check if Guild and User exist
        if gid in self.data and uid in self.data[gid]:
            if command_name in self.data[gid][uid]:
                self.data[gid][uid].remove(command_name)

                # Cleanup: If list is empty, remove the user key
                if not self.data[gid][uid]:
                    del self.data[gid][uid]

                # Cleanup: If guild is empty, remove the guild key
                if not self.data[gid]:
                    del self.data[gid]

                self._save()
                return True
        return False

    def is_blocked(self, guild_id: int, user_id: int, command_name: str) -> bool:
        gid = str(guild_id)
        uid = str(user_id)

        # 1. Check Guild
        if gid not in self.data:
            return False

        # 2. Check User
        if uid not in self.data[gid]:
            return False

        # 3. Check Command
        user_blocks = self.data[gid][uid]
        return command_name in user_blocks or "all" in user_blocks


blacklist_store = BlacklistManager()

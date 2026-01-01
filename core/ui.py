import discord


class UI:
    @staticmethod
    def success(title: str, description: str):
        return discord.Embed(
            title=f"✅ {title}", description=description, color=discord.Color.green()
        )

    @staticmethod
    def error(title: str, error: str):
        return discord.Embed(
            title=f"❌ {title}", description=f"```{error}```", color=discord.Color.red()
        )

    @staticmethod
    def warn(title: str, message: str):
        return discord.Embed(
            title=f"⚠️ {title}", description=f"{message}", color=discord.Color.gold()
        )

    @staticmethod
    def info(title: str, message: str):
        return discord.Embed(
            title=f"ℹ️ {title}", description=f"{message}", color=discord.Color.blue()
        )

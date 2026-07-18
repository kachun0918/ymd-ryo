import discord
from discord.ext import commands

from core.server_settings import server_settings

from .logger import setup_logging

# Logger
setup_logging()

# Intents
intents = discord.Intents.default()
intents.message_content = True


# Instantiate
def get_prefix(bot, message):
    if not message.guild:
        return "!"

    return server_settings.get_prefix(message.guild.id)

# Custom Help Command
class InformativeHelp(commands.MinimalHelpCommand):
    """Custom help command with clearer summaries and usage."""

    @staticmethod
    def _category_name(cog) -> str:
        if cog is None:
            return "General"

        name = cog.qualified_name
        if name.lower() == "dllm":
            return "DLLM"
        return name

    def _brief_for(self, command: commands.Command) -> str:
        return command.brief or command.short_doc or "No description."

    async def send_bot_help(self, mapping):
        prefix = self.context.clean_prefix
        lines = [
            "Command Help",
            f"Prefix: `{prefix}`",
            "",
        ]

        for cog, raw_commands in sorted(
            mapping.items(), key=lambda item: self._category_name(item[0]).lower()
        ):
            filtered = await self.filter_commands(raw_commands, sort=True)
            if not filtered:
                continue

            lines.append(f"{self._category_name(cog)}:")
            for command in filtered:
                lines.append(f"  {command.name:<10} {self._brief_for(command)}")
            lines.append("")

        lines.extend(
            [
                f"Tips: `{prefix}help <command>` for usage and examples.",
                f"      `{prefix}help <category>` for commands in one category.",
            ]
        )
        await self.get_destination().send("\n".join(lines))

    async def send_cog_help(self, cog):
        prefix = self.context.clean_prefix
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        lines = [f"{self._category_name(cog)} Commands", ""]

        if cog.description:
            desc_line = next((line.strip() for line in cog.description.splitlines() if line.strip()), "")
            if desc_line:
                lines.extend([desc_line, ""])

        if not filtered:
            lines.append("No commands available.")
        else:
            for command in filtered:
                lines.append(f"- `{command.name}`: {self._brief_for(command)}")

        lines.extend(["", f"Use `{prefix}help <command>` for details on one command."])
        await self.get_destination().send("\n".join(lines))

    async def send_command_help(self, command):
        prefix = self.context.clean_prefix
        lines = [
            f"Command: `{command.qualified_name}`",
            f"Description: {self._brief_for(command)}",
            f"Usage: `{prefix}{command.qualified_name} {command.signature}`".rstrip(),
        ]

        if command.aliases:
            lines.append(f"Aliases: {', '.join(f'`{alias}`' for alias in command.aliases)}")

        if command.help and command.help != command.short_doc:
            lines.extend(["", command.help.strip()])

        await self.get_destination().send("\n".join(lines))

    async def send_group_help(self, group):
        await self.send_command_help(group)


bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=InformativeHelp())


# Define Standard Events
@bot.event
async def on_ready():
    import logging

    logger = logging.getLogger("discord")
    logger.info("---------------------------------------------")
    logger.info(f"👤 Logged in as: {bot.user.name}")
    logger.info(f"🆔 ID: {bot.user.id}")
    logger.info("---------------------------------------------")

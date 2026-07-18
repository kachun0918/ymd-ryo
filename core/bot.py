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
        all_commands = []
        for _, raw_commands in mapping.items():
            filtered = await self.filter_commands(raw_commands, sort=True)
            all_commands.extend(filtered)

        all_commands.sort(key=lambda cmd: cmd.name.lower())
        embed = discord.Embed(
            title="How to use Yamada Ryo Bot",
            description="Useful Commands",
            color=discord.Color.blurple(),
        )

        # Discord supports up to 25 fields per embed.
        for command in all_commands[:25]:
            brief = self._brief_for(command)
            if len(brief) > 80:
                brief = brief[:77].rstrip() + "..."
            embed.add_field(name=f"{prefix}{command.name}", value=brief, inline=True)

        embed.set_footer(
            text=(
                f"Prefix: {prefix}  |  "
                f"{prefix}help <command> for details  |  "
                f"{prefix}help <category> by category"
            )
        )
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        prefix = self.context.clean_prefix
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        embed = discord.Embed(
            title=f"{self._category_name(cog)} Commands",
            color=discord.Color.blurple(),
        )

        if cog.description:
            desc_line = next(
                (line.strip() for line in cog.description.splitlines() if line.strip()), ""
            )
            if desc_line:
                embed.description = desc_line

        if not filtered:
            embed.add_field(name="Commands", value="No commands available.", inline=False)
        else:
            value = "\n".join(
                f"`{command.name}` - {self._brief_for(command)}" for command in filtered
            )
            embed.add_field(name="Commands", value=value, inline=False)

        embed.set_footer(text=f"Use {prefix}help <command> for one command detail")
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        prefix = self.context.clean_prefix
        embed = discord.Embed(
            title=f"Command: {command.qualified_name}",
            description=self._brief_for(command),
            color=discord.Color.blurple(),
        )
        usage = f"`{prefix}{command.qualified_name} {command.signature}`".rstrip()
        embed.add_field(name="Usage", value=usage, inline=False)

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join(f"`{alias}`" for alias in command.aliases),
                inline=False,
            )

        if command.help and command.help != command.short_doc:
            embed.add_field(name="Details", value=command.help.strip()[:1024], inline=False)

        await self.get_destination().send(embed=embed)

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

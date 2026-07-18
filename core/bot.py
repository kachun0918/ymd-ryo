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
    def _brief_for(self, command: commands.Command) -> str:
        return command.brief or command.short_doc or "No description."

    def _example_for(self, command: commands.Command, prefix: str) -> str:
        custom_examples = {
            "help": f"{prefix}help  |  {prefix}help 9up",
            "alias": f"{prefix}alias @user nickname",
            "unalias": f"{prefix}unalias @user nickname",
            "listalias": f"{prefix}listalias @user",
            "save": f"{prefix}save   (reply to a message)",
            "9up": f"{prefix}9up  |  {prefix}9up @user  |  {prefix}9up alias -f",
            "9uplist": f"{prefix}9uplist @user",
            "9uptop": f"{prefix}9uptop  |  {prefix}9uptop @user",
            "9updel": f"{prefix}9updel @user",
            "dllm": f"{prefix}dllm",
        }
        if command.name in custom_examples:
            return custom_examples[command.name]

        signature = f" {command.signature}" if command.signature else ""
        return f"{prefix}{command.qualified_name}{signature}".strip()

    @staticmethod
    def _codeblock_chunks(lines: list[str], lang: str = "text", max_len: int = 1024) -> list[str]:
        chunks = []
        current = []
        fence_overhead = len(f"```{lang}\n\n```")

        for line in lines:
            candidate = "\n".join(current + [line])
            if len(candidate) + fence_overhead > max_len and current:
                chunks.append(f"```{lang}\n" + "\n".join(current) + "\n```")
                current = [line]
            else:
                current.append(line)

        if current:
            chunks.append(f"```{lang}\n" + "\n".join(current) + "\n```")

        return chunks

    async def send_bot_help(self, mapping):
        prefix = self.context.clean_prefix
        all_commands = []
        for _, raw_commands in mapping.items():
            filtered = await self.filter_commands(raw_commands, sort=True)
            all_commands.extend(filtered)

        all_commands.sort(key=lambda cmd: cmd.name.lower())
        embed = discord.Embed(
            title="How to use Yamada Ryo Bot",
            description="All user commands with quick examples",
            color=discord.Color.blurple(),
        )

        commands_lines = []
        for command in all_commands:
            brief = self._brief_for(command)
            if len(brief) > 70:
                brief = brief[:67].rstrip() + "..."
            commands_lines.append(f"{prefix}{command.name:<10} - {brief}")

        examples_lines = [self._example_for(command, prefix) for command in all_commands]

        for idx, block in enumerate(self._codeblock_chunks(commands_lines, "text"), start=1):
            label = "Commands" if idx == 1 else f"Commands (cont. {idx})"
            embed.add_field(name=label, value=block, inline=False)

        for idx, block in enumerate(self._codeblock_chunks(examples_lines, "bash"), start=1):
            label = "Examples" if idx == 1 else f"Examples (cont. {idx})"
            embed.add_field(name=label, value=block, inline=False)

        embed.set_footer(
            text=(
                f"Prefix: {prefix} | {prefix}help <command> for full details"
            )
        )
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        prefix = self.context.clean_prefix
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        category_name = cog.qualified_name if cog else "General"
        embed = discord.Embed(
            title=f"{category_name} Commands",
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
            command_lines = [
                f"{prefix}{command.name:<10} - {self._brief_for(command)}" for command in filtered
            ]
            example_lines = [self._example_for(command, prefix) for command in filtered]
            for idx, block in enumerate(self._codeblock_chunks(command_lines, "text"), start=1):
                label = "Commands" if idx == 1 else f"Commands (cont. {idx})"
                embed.add_field(name=label, value=block, inline=False)
            for idx, block in enumerate(self._codeblock_chunks(example_lines, "bash"), start=1):
                label = "Examples" if idx == 1 else f"Examples (cont. {idx})"
                embed.add_field(name=label, value=block, inline=False)

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
        embed.add_field(
            name="Example",
            value=f"```bash\n{self._example_for(command, prefix)}\n```",
            inline=False,
        )

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

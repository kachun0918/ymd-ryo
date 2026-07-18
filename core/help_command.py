import discord
from discord.ext import commands
from textwrap import dedent


class InformativeHelp(commands.MinimalHelpCommand):
    CATEGORY_ORDER = [
        ("quotes", "Quotes"),
        ("dllm", "DLLM"),
        ("alias", "Alias"),
    ]
    CATEGORY_DESCRIPTIONS = {
        "quotes": "引用金句",
        "dllm": "屌你老母",
        "alias": "別名",
    }
    CATEGORY_HELP_TOKENS = {
        "Quotes": "quotes",
        "DLLM": "dllm",
        "Alias": "alias",
    }
    EXAMPLE_TEMPLATES = {
        "help": """
            # Show global help
            {p}help

            # Show category help
            {p}help Quotes

            # Show command help
            {p}help 9up
        """,
        "alias": "{p}alias @user",
        "unalias": "{p}unalias @user nickname",
        "listalias": "{p}listalias @user",
        "save": "{p}save",
        "9up": """
            # Fetch a quote from a random member
            {p}9up

            # Fetch a quote from a specific member
            {p}9up [@user|alias|id]

            # Helper flag
            {p}9up [@user|alias|id] -f
        """,
        "9uplist": "{p}9uplist @user",
        "9uptop": """
            # Show top quotes
            {p}9uptop

            # Show top quotes for a specific member
            {p}9uptop @user
        """,
        "9updel": "{p}9updel @user",
        "dllm": "{p}dllm",
    }

    """
    Returns one-line description text for a command.
    Priority: command.brief > command.short_doc > "No description."
    """
    def _brief_for(self, command: commands.Command) -> str:
        return command.brief or command.short_doc or "No description."

    @staticmethod
    def _clean_example(text: str) -> str:
        return dedent(text).strip()

    def _format_example(self, template: str, prefix: str) -> str:
        return self._clean_example(template).format(p=prefix)

    # Returns a multi-line example usage text for a command.
    def _example_for(self, command: commands.Command, prefix: str) -> str:
        template = self.EXAMPLE_TEMPLATES.get(command.name)
        if template is not None:
            return self._format_example(template, prefix)

        signature = f" {command.signature}" if command.signature else ""
        return f"{prefix}{command.qualified_name}{signature}".strip()

    def _resolve_command_by_name_or_alias(self, raw: str):
        lowered = raw.lower()
        cmd = self.context.bot.get_command(raw)
        if cmd is not None:
            return cmd

        for item in self.context.bot.walk_commands():
            aliases = [alias.lower() for alias in item.aliases]
            if item.qualified_name.lower() == lowered or item.name.lower() == lowered:
                return item
            if lowered in aliases:
                return item
        return None


    """
    Case-insensitive lookup of a loaded cog by name
    Loops through self.context.bot.cogs.values()
    Returns matched cog object or None
    Used when routing !help quotes, !help dllm, etc.
    """
    def _find_cog_by_key(self, key: str):
        lowered = key.lower()
        for cog in self.context.bot.cogs.values():
            if cog.qualified_name.lower() == lowered:
                return cog
        return None

    """
    Main command callback that handles !help and !help <category>
    Routes to cog or command help based on input.
    """
    async def command_callback(self, ctx, /, *, command=None):
        await self.prepare_help_command(ctx, command)

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        raw = command.strip()

        # Category routing is explicit to avoid alias/command ambiguity.
        if raw in self.CATEGORY_HELP_TOKENS:
            cog = self._find_cog_by_key(self.CATEGORY_HELP_TOKENS[raw])
            if cog is not None:
                return await self.send_cog_help(cog)

        cmd = self._resolve_command_by_name_or_alias(raw)
        if cmd is not None:
            return await self.send_command_help(cmd)

        return await self.send_error_message(self.command_not_found(command))

    
    # Renders top-level !help.
    async def send_bot_help(self, mapping):
        prefix = self.context.clean_prefix
        embed = discord.Embed(
            title="山田涼",
            color=discord.Color.blurple(),
        )

        for key, label in self.CATEGORY_ORDER:
            cog = self._find_cog_by_key(key)
            if cog is None:
                continue
            desc = self.CATEGORY_DESCRIPTIONS.get(key, "Commands")
            embed.add_field(
                name=label,
                value=f"{desc}\n\n`{prefix}help {label}`",
                inline=True,
            )

        await self.get_destination().send(embed=embed)

    # Renders category-level help
    async def send_cog_help(self, cog):
        prefix = self.context.clean_prefix
        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        embed = discord.Embed(
            title=f"{cog.qualified_name}",
            color=discord.Color.blurple(),
        )

        if not filtered:
            embed.description = "No commands available."
            return await self.get_destination().send(embed=embed)

        names = [f"`{prefix}{command.name}`" for command in filtered]
        embed.description = ", ".join(names)[:4096]
        await self.get_destination().send(embed=embed)

    # Renders command-level help
    async def send_command_help(self, command):
        prefix = self.context.clean_prefix
        if command.qualified_name == "help":
            usage_text = f"{prefix}help [指令/類別]"
        else:
            usage_text = f"{prefix}{command.qualified_name}"
            if command.signature:
                usage_text += f" {command.signature}"

        embed = discord.Embed(
            title=f"{command.qualified_name}",
            description=self._brief_for(command),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Usage", value=f"`{usage_text}`", inline=False)
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

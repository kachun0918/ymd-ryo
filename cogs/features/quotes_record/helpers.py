"""
Quotes helper utilities.

Technical:
- Contains reusable validation and webhook-send helpers for quotes workflow.

Plain language:
- Small support functions used by the quotes feature.
- Keeps main command file cleaner and easier to read.
"""

import logging

import discord

logger = logging.getLogger("discord.quotes.helpers")


def is_saveable(msg: discord.Message) -> bool:
    """
    Validate whether a message can be saved as a quote.

    Plain language:
    - Blocks bots/webhooks/links/empty text to keep quote quality clean.
    """
    if msg.author.bot:
        return False
    if msg.webhook_id is not None:
        return False
    if "http://" in msg.content or "https://" in msg.content:
        return False
    if not msg.content or not msg.content.strip():
        return False

    return True


async def send_mimic_message(
    ctx, member: discord.Member, content: str, footer_embed: discord.Embed = None
):
    """
    Send quote output through webhook mimic when possible.

    Technical:
    - Uses per-channel webhook and thread-aware routing.
    - Falls back to embed when webhook permission or send fails.

    Plain language:
    - Tries to make the quote look like the original speaker.
    - If that is not possible, it still sends a readable embed.
    """

    perms = ctx.channel.permissions_for(ctx.guild.me)
    if not perms.manage_webhooks:
        await _send_fallback_embed(ctx, member, content, footer_embed)
        return

    try:
        if isinstance(ctx.channel, discord.Thread):
            dest_channel = ctx.channel.parent
            is_thread = True
        else:
            dest_channel = ctx.channel
            is_thread = False

        webhooks = await dest_channel.webhooks()
        webhook = discord.utils.get(webhooks, name="MimicBot")

        if not webhook:
            webhook = await dest_channel.create_webhook(name="MimicBot")

        username = f"🗣️ {member.display_name}"
        avatar_url = member.display_avatar.url if hasattr(member.display_avatar, "url") else None

        await webhook.send(
            content=content,
            username=username,
            avatar_url=avatar_url,
            thread=ctx.channel if is_thread else discord.utils.MISSING,
            embed=footer_embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    except Exception as e:
        logger.warning(f"Webhook mimic failed: {e}. Falling back to Embed.")
        await _send_fallback_embed(ctx, member, content, footer_embed)


async def _send_fallback_embed(
    ctx, member: discord.Member, content: str, footer_embed: discord.Embed = None
):
    """
    Send standard embed when webhook mimic path is unavailable.
    """
    mimic_name = f"🗣️ {member.display_name}"

    embed = discord.Embed(
        description=content, color=member.color if member else discord.Color.default()
    )

    embed.set_author(
        name=mimic_name,
        icon_url=member.display_avatar.url if hasattr(member.display_avatar, "url") else None,
    )

    if footer_embed:
        for field in footer_embed.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)

    await ctx.send(embed=embed)

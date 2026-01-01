import logging

import discord

logger = logging.getLogger("discord.quotes.helpers")


def is_saveable(msg: discord.Message) -> bool:
    """
    Validates if a message is eligible to be saved as a quote.
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
    Attempts to send a message via Webhook to mimic the user.
    Falls back to a standard Embed if permissions are missing or webhook fails.
    Supports Threads automatically.
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
    Sends a standard Embed when Webhooks don't work.
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

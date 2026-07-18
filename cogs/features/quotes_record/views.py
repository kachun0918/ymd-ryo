"""
Interactive views for the quotes feature.

Technical:
- Defines paginated list view and delete-confirm workflow using Discord UI components.
- Enforces quote deletion permissions at interaction time.

Plain language:
- This file powers the clickable buttons for browsing and deleting quotes.
- It makes quote management easier than typing everything manually.
"""

import aiosqlite
import discord

from core.config import settings


class PaginationView(discord.ui.View):
    """
    Generic quote pagination view used by quote listing UIs.

    Plain language:
    - Lets users browse quotes page by page using buttons.
    """

    def __init__(self, data, title, member, per_page=5):
        super().__init__(timeout=60)
        self.data = data
        self.title = title
        self.member = member
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = max(1, (len(data) + per_page - 1) // per_page)
        self.update_buttons()

    def update_buttons(self):
        """Update button enabled state and page counter text."""
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1
        self.counter_button.label = f"Page {self.current_page + 1}/{self.total_pages}"

    def create_embed(self):
        """Build the embed content for the current page."""
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.data[start:end]

        embed = discord.Embed(
            title=f"{self.title} ({len(self.data)} total)", color=self.member.color
        )
        embed.set_thumbnail(url=self.member.display_avatar.url)

        num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        for i, item in enumerate(page_items):
            content, added_ts, adder_id, uses, *ignore = item

            clean_content = content.replace("\n", " ")
            if len(clean_content) > 60:
                display_text = clean_content[:57] + "..."
            else:
                display_text = clean_content

            adder_str = f"<@{adder_id}>" if adder_id else "System"
            time_str = f"<t:{added_ts}:R>" if added_ts else "Unknown date"

            row_emoji = num_emojis[i] if i < len(num_emojis) else "🔹"

            embed.add_field(
                name=f"{row_emoji}",
                value=f"{display_text}\n{uses} times\n*{time_str} by {adder_str}*",
                inline=False,
            )

        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.grey)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.grey, disabled=True)
    async def counter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.grey)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_timeout(self):
        """Disable view buttons when interaction window expires."""
        for item in self.children:
            item.disabled = True
        try:
            pass
        except Exception:
            pass


class DeleteQuoteView(PaginationView):
    """
    Pagination view with delete-selection actions.

    Plain language:
    - Same as normal list view, but adds number buttons to choose a quote for deletion.
    """

    def __init__(self, data, title, member, ctx, db_path):
        super().__init__(data, title, member, per_page=5)
        self.ctx = ctx
        self.db_path = db_path
        self.selected_item = None
        self.message = None

        # Add selection buttons (1-5)
        for i in range(1, 6):
            button = discord.ui.Button(
                label=str(i), style=discord.ButtonStyle.blurple, custom_id=f"select_{i}"
            )
            button.callback = self.select_callback
            self.add_item(button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Allow only command invoker to control this interactive menu."""
        # Only the person who ran the command can use the menu
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                "❌ You cannot control this menu.", ephemeral=True
            )
            return False
        return True

    async def select_callback(self, interaction: discord.Interaction):
        """Handle quote-selection button click and open confirmation prompt."""
        # 1. Figure out which button was clicked
        try:
            button_num = int(interaction.data["custom_id"].split("_")[1]) - 1
        except (ValueError, IndexError):
            return

        start_index = self.current_page * self.per_page
        item_index = start_index + button_num

        # 2. Safety Check
        if item_index >= len(self.data):
            await interaction.response.send_message("❌ Invalid selection.", ephemeral=True)
            return

        # 3. Get Quote Data
        # Format: (content, added_ts, adder_id, uses, quote_id)
        quote = self.data[item_index]
        self.selected_item = quote

        content, _, adder_id, _, quote_id = quote

        # 4. --- INTEGRATED IAM PERMISSION CHECK ---

        # Check A: Is Bot Owner? (From settings.OWNER_ID)
        is_owner = interaction.user.id == settings.OWNER_ID

        # Check B: Is Admin? (Has the specific role defined in settings)
        is_admin = False
        if interaction.guild:
            # Check if user has the specific Admin Role Name
            role = discord.utils.get(interaction.user.roles, name=settings.ADMIN_ROLE_NAME)
            if role:
                is_admin = True
            # Optional: Also allow actual "Administrator" permission as a fallback
            if interaction.user.guild_permissions.administrator:
                is_admin = True

        # Check C: Is the Original Adder?
        is_adder = interaction.user.id == adder_id

        if not (is_owner or is_admin or is_adder):
            await interaction.response.send_message(
                f"⛔ **Permission Denied.**\nOnly the **Bot Owner**, **{settings.ADMIN_ROLE_NAME}**, or the **original adder** can delete this.",
                ephemeral=True,
            )
            return

        # 5. Confirmation Dialog
        confirm_view = ConfirmDeleteView(self)
        await interaction.response.send_message(
            f"⚠️ **Delete this quote?**\n> {content}", view=confirm_view, ephemeral=True
        )

    async def delete_quote(self, interaction: discord.Interaction):
        """Delete selected quote and refresh parent menu state."""
        if not self.selected_item:
            return

        # Get ID (last element)
        quote_id = self.selected_item[-1]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            await db.commit()

        # Remove from local data list
        self.data.remove(self.selected_item)

        # Recalculate pages
        self.total_pages = max(1, (len(self.data) + self.per_page - 1) // self.per_page)

        # If page is now empty, go back one
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)
        self.update_buttons()
        await interaction.response.edit_message(content="✅ **Deleted!**", view=None)

        # Refresh the main list embed
        if self.message:
            await self.message.edit(embed=self.create_embed(), view=self)


class ConfirmDeleteView(discord.ui.View):
    """
    Confirmation buttons for destructive quote delete action.

    Plain language:
    - Asks for one final yes/no before removing a quote.
    """

    def __init__(self, parent_view):
        super().__init__(timeout=30)
        self.parent = parent_view

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm deletion and execute parent delete flow."""
        await self.parent.delete_quote(interaction)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel deletion and close confirmation UI."""
        await interaction.response.edit_message(content="❌ Cancelled.", view=None)
        self.stop()

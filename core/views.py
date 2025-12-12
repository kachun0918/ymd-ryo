import discord


class PaginationView(discord.ui.View):
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
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.total_pages - 1
        self.counter_button.label = f"Page {self.current_page + 1}/{self.total_pages}"

    def create_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_items = self.data[start:end]

        embed = discord.Embed(
            title=f"{self.title} ({len(self.data)} total)", color=self.member.color
        )
        embed.set_thumbnail(url=self.member.display_avatar.url)

        num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

        for i, item in enumerate(page_items):
            content, added_ts, adder_id, uses = item

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
        for item in self.children:
            item.disabled = True
        try:
            pass
        except Exception:
            pass

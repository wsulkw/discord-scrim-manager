from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from main import ScrimBot


def is_valid_datetime_format(time_str: str) -> bool:
    try:
        datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        return True
    except ValueError:
        return False


class ScrimCommands(commands.Cog):
    def __init__(self, bot: ScrimBot):
        self.bot = bot

    @app_commands.command(name="create_scrim", description="Create new scrim")
    async def create_scrim(self,
                           interaction: discord.Interaction,
                           title: str,
                           game_mode: str,
                           time: str,
                           max_players: int):
        if not is_valid_datetime_format(time):
            await interaction.response.send_message(
                "Invalid time format! Please use `YYYY-MM-DD HH:MM` (e.g., `2024-12-25 15:30`).", ephemeral=True)
            return

        time_obj = datetime.strptime(time, "%Y-%m-%d %H:%M")
        if time_obj < datetime.now():
            await interaction.response.send_message("Please select a time in the future.", ephemeral=True)
            return

        if max_players < 2 or max_players % 2 != 0:
            await interaction.response.send_message("Max players must be at least 2 and an even number.",
                                                    ephemeral=True)
            return

        scrim_id = self.bot.db.insert_scrim(title, game_mode, time, max_players, interaction.user)

        embed = discord.Embed(
            title="Scrim Created Successfully!",
            description=f"**{title}** - {game_mode}",
            color=0x00ff00
        )
        embed.add_field(name="Scheduled", value=f"<t:{int(time_obj.timestamp())}:F>", inline=True)
        embed.add_field(name="Max Players", value=str(max_players), inline=True)
        embed.add_field(name="Scrim ID", value=str(scrim_id), inline=True)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join_scrim", description="Join existing scrim")
    async def join_scrim(self,
                         interaction: discord.Interaction,
                         scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return
        if scrim['status'] in ['completed', 'active', 'cancelled']:
            await interaction.response.send_message("This scrim is no longer accepting players.", ephemeral=True)
            return
        if self.bot.db.is_user_in_scrim(scrim_id, interaction.user.id):
            await interaction.response.send_message("You're already registered for this scrim.", ephemeral=True)
            return
        if scrim['status'] == 'full':
            await interaction.response.send_message("This scrim is full! Try joining another one.", ephemeral=True)
            return

        self.bot.db.insert_scrim_player(scrim_id, interaction.user)

        current_count = self.bot.db.get_scrim_player_count(scrim_id)
        if current_count == scrim['max_players']:
            self.bot.db.update_scrim_status(scrim_id, "full")

        embed = discord.Embed(
            title="Successfully Joined!",
            description=f"You've been added to Scrim #{scrim_id}",
            color=0x00ff00
        )
        embed.add_field(name="Players", value=f"{current_count}/{scrim['max_players']}", inline=True)
        embed.set_footer(text="You'll be notified when the scrim starts!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leave_scrim", description="Leave a scrim")
    async def leave_scrim(self,
                          interaction: discord.Interaction,
                          scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        user = interaction.user
        if not self.bot.db.is_user_in_scrim(scrim_id, user.id):
            await interaction.response.send_message("You're not registered for this scrim.", ephemeral=True)
            return

        self.bot.db.delete_scrim_player(scrim_id, user.id)
        if scrim['status'] == 'full':
            self.bot.db.update_scrim_status(scrim_id, "open")

        await interaction.response.send_message(
            f"Successfully left Scrim #{scrim_id}. You can rejoin anytime before it starts!", ephemeral=True)

    @app_commands.command(name="list_scrims", description="View all active scrims")
    async def list_scrims(self,
                          interaction: discord.Interaction):
        scrims = self.bot.db.get_active_scrims()

        if not scrims:
            embed = discord.Embed(
                title="Active Scrims",
                description="No active scrims found.",
                color=0x99ccff
            )
            await interaction.response.send_message(embed=embed)
            return

        per_page = 5
        pages = [scrims[i:i + per_page] for i in range(0, len(scrims), per_page)]
        current_page = 0

        def get_page_content(page_num):
            embed = discord.Embed(
                title="Active Scrims",
                color=0x0099ff
            )
            for i, scrim in enumerate(pages[page_num]):
                status_emoji = {
                    'open': '🟢',
                    'full': '🔴',
                    'active': '🔵'
                }.get(scrim['status'], '⚪')

                embed.add_field(
                    name=f"{status_emoji} Scrim #{scrim['id']} - {scrim['title']}",
                    value=f"**Mode:** {scrim['game_mode']}\n**Players:** {scrim['player_count']}/{scrim['max_players']}\n**Status:** {scrim['status'].title()}",
                    inline=False
                )
            embed.set_footer(text=f"Page {page_num + 1}/{len(pages)} • Use /scrim_info [id] for details")
            return embed

        class PaginationView(discord.ui.View):
            @discord.ui.button(label="Previous")
            async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal current_page
                current_page = (current_page - 1) % len(pages)
                await interaction.response.edit_message(embed=get_page_content(current_page), view=self)

            @discord.ui.button(label="Next")
            async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                nonlocal current_page
                current_page = (current_page + 1) % len(pages)
                await interaction.response.edit_message(embed=get_page_content(current_page), view=self)

        await interaction.response.send_message(embed=get_page_content(0), view=PaginationView())

    @app_commands.command(name="scrim_info", description="Detailed scrim information")
    async def scrim_info(self,
                         interaction: discord.Interaction,
                         scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Scrim #{scrim_id} Details",
            description=scrim['title'],
            color=0x0099ff
        )
        embed.add_field(name="Game Mode", value=scrim['game_mode'], inline=True)
        embed.add_field(name="Players", value=f"{scrim['player_count']}/{scrim['max_players']}", inline=True)
        embed.add_field(name="Status", value=scrim['status'].title(), inline=True)
        embed.add_field(name="Scheduled",
                        value=f"<t:{int(datetime.strptime(scrim['scheduled_time'], '%Y-%m-%d %H:%M').timestamp())}:F>",
                        inline=False)

        try:
            creator = await self.bot.fetch_user(scrim['creator_id'])
            creator_name = creator.display_name
        except:
            creator_name = f"User {scrim['creator_id']}"

        embed.set_footer(text=f"Created by {creator_name} • ID: {scrim_id}")

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog loaded")


async def setup(bot):
    await bot.add_cog(ScrimCommands(bot))

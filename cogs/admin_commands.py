import random

import discord
from discord import app_commands
from discord.ext import commands

from main import ScrimBot

SCRIM_ADMIN_ROLE_ID = 1387887017882554499


def has_scrim_permissions():
    async def predicate(interaction: discord.Interaction):
        if discord.utils.get(interaction.user.roles, id=SCRIM_ADMIN_ROLE_ID):
            return True

        scrim = interaction.client.db.get_scrim_by_id(interaction.namespace.scrim_id)
        if scrim and scrim['creator_id'] == interaction.user.id:
            return True
        return False

    return app_commands.check(predicate)


class AdminCommands(commands.Cog):
    def __init__(self, bot: ScrimBot):
        self.bot = bot

    @app_commands.command(name="start_scrim", description="Starts a scrim")
    @has_scrim_permissions()
    async def start_scrim(self,
                          interaction: discord.Interaction,
                          scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        if scrim['status'] not in ['open', 'full']:
            await interaction.response.send_message(f"Cannot start scrim - status is '{scrim['status']}'.",
                                                    ephemeral=True)
            return

        waiting_room_vc = interaction.guild.get_channel(self.bot.waiting_room_vc_id)

        players = []
        for member in waiting_room_vc.members:
            if self.bot.db.is_user_in_scrim(scrim_id, member.id):
                players.append(member)

        if len(players) < 2:
            await interaction.response.send_message(
                "Can't start scrim - need at least 2 players in the waiting room voice channel.", ephemeral=True)
            return

        try:
            guild = interaction.guild
            category = await guild.create_category(f"Scrim {scrim_id}")
            team1_vc = await guild.create_voice_channel("Team 1 🔴", category=category)
            team2_vc = await guild.create_voice_channel("Team 2 🔵", category=category)

            self.bot.db.update_scrim_channels(scrim_id, category.id, team1_vc.id, team2_vc.id)
        except discord.Forbidden:
            await interaction.response.send_message("Bot lacks permissions to create voice channels.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Failed to create voice channels. Please try again.",
                                                    ephemeral=True)
            return

        random.shuffle(players)
        mid = len(players) // 2
        team1 = players[:mid]
        team2 = players[mid:]

        if random.choice([True, False]):
            team1, team2 = team2, team1

        for player in team1:
            self.bot.db.update_player_team(scrim_id, player.id, 1)
            try:
                await player.move_to(team1_vc)
            except (discord.Forbidden, discord.HTTPException):
                pass
        for player in team2:
            self.bot.db.update_player_team(scrim_id, player.id, 2)
            try:
                await player.move_to(team2_vc)
            except (discord.Forbidden, discord.HTTPException):
                pass

        self.bot.db.update_scrim_status(scrim_id, "active")

        embed = discord.Embed(title=f"Scrim #{scrim_id} Started!",
                              description="Teams have been created and players moved to their channels. Good luck!",
                              color=0x00ff00)
        embed.add_field(name="🔴 Team 1", value="\n".join([f"• {player.display_name}" for player in team1]), inline=True)
        embed.add_field(name="🔵 Team 2", value="\n".join([f"• {player.display_name}" for player in team2]), inline=True)
        embed.set_footer(text=f"Started by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cancel_scrim", description="Cancels an upcoming scrim")
    @has_scrim_permissions()
    async def cancel_scrim(self,
                           interaction: discord.Interaction,
                           scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        category_id = scrim["category_id"]
        if category_id:
            category = interaction.guild.get_channel(category_id)
            if category:
                await category.delete()

        self.bot.db.update_scrim_status(scrim_id, "cancelled")

        embed = discord.Embed(
            title="Scrim Cancelled",
            description=f"Scrim #{scrim_id} has been cancelled by an administrator.",
            color=0xff0000)
        embed.set_footer(text="You've been automatically removed from this scrim.")

        players = self.bot.db.get_scrim_players(scrim_id)
        for player in players:
            try:
                member = interaction.guild.get_member(player['player_id'])
                if member:
                    await member.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

        await interaction.response.send_message(
            f"Scrim #{scrim_id} has been cancelled and all players have been notified.", ephemeral=True)

    @app_commands.command(name="end_scrim", description="Ends a scrim")
    @has_scrim_permissions()
    async def end_scrim(self,
                        interaction: discord.Interaction,
                        scrim_id: int):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        category_id = scrim["category_id"]
        team1_channel_id = scrim["team1_vc_id"]
        team2_channel_id = scrim["team2_vc_id"]
        if category_id:
            category = interaction.guild.get_channel(category_id)
            if category:
                await category.delete()
        if team1_channel_id:
            team1_channel = interaction.guild.get_channel(team1_channel_id)
            if team1_channel:
                await team1_channel.delete()
        if team2_channel_id:
            team2_channel = interaction.guild.get_channel(team2_channel_id)
            if team2_channel:
                await team2_channel.delete()

        self.bot.db.update_scrim_status(scrim_id, "completed")

        players = self.bot.db.get_scrim_players(scrim_id)
        embed = discord.Embed(title="Scrim Completed",
                              description=f"Scrim #{scrim_id} has ended. Thanks for playing!",
                              color=0x0099ff)
        embed.add_field(name="🔴 Team 1",
                        value="\n".join([f"• {player['player_name']}" for player in players if player['team'] == 1]),
                        inline=True)
        embed.add_field(name="🔵 Team 2",
                        value="\n".join([f"• {player['player_name']}" for player in players if player['team'] == 2]),
                        inline=True)
        embed.set_footer(text="GG everyone!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="message_scrim", description="Send a custom message to all players in a scrim")
    async def message_scrim(self,
                            interaction: discord.Interaction,
                            scrim_id: int,
                            message: str):
        scrim = self.bot.db.get_scrim_by_id(scrim_id)
        if not scrim:
            await interaction.response.send_message("Scrim not found. Please check the ID and try again.",
                                                    ephemeral=True)
            return

        if scrim['creator_id'] != interaction.user.id:
            await interaction.response.send_message("Only the scrim creator can send messages to participants.",
                                                    ephemeral=True)
            return

        players = self.bot.db.get_scrim_players(scrim_id)
        if not players:
            await interaction.response.send_message("No players found in this scrim.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Message from Scrim #{scrim_id} Creator",
            description=message,
            color=0xffaa00
        )
        embed.set_footer(text=f"From: {interaction.user.display_name}")

        sent_count = 0
        for player in players:
            try:
                member = interaction.guild.get_member(player['player_id'])
                if member:
                    await member.send(embed=embed)
                    sent_count += 1
            except discord.Forbidden:
                continue

        await interaction.response.send_message(
            f"Message sent to {sent_count}/{len(players)} players in Scrim #{scrim_id}.",
            ephemeral=True
        )

    @app_commands.command(name="purge_old_scrims", description="Clean up old completed scrims (admin only)")
    @has_scrim_permissions()
    async def purge_old_scrims(self,
                               interaction: discord.Interaction):
        deleted_count = self.bot.db.delete_old_scrims()

        await interaction.response.send_message(
            f"Purged {deleted_count} old scrims and cleaned up player records.",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog loaded")


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))

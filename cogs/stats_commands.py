import discord
from discord import app_commands
from discord.ext import commands

from main import ScrimBot


class StatsCommands(commands.Cog):
    def __init__(self, bot: ScrimBot):
        self.bot = bot

    @app_commands.command(name="my_scrims", description="Personal scrim history")
    async def my_scrims(self,
                        interaction: discord.Interaction):
        scrims = self.bot.db.get_scrims_by_user(interaction.user.id)
        if not scrims:
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Scrim History",
                description="You haven't joined any scrims yet.",
                color=0x99ccff
            )
        else:
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Scrim History",
                description=f"Total scrims played: {len(scrims)}",
                color=0x0099ff
            )
            scrim_list = "\n".join([f"• Scrim #{scrim['scrim_id']}" for scrim in scrims])
            embed.add_field(name="Your Scrims", value=scrim_list, inline=False)

        await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} cog loaded")


async def setup(bot):
    await bot.add_cog(StatsCommands(bot))

import os

import discord
import dotenv
from discord.ext import commands

from database.database import Database

dotenv.load_dotenv()

WAITING_ROOM_VC_ID = 1162960960907137038


class ScrimBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(command_prefix='.', intents=intents)
        self.db = Database()

        self.waiting_room_vc_id = WAITING_ROOM_VC_ID

    async def setup_hook(self) -> None:
        try:
            await self.load_extension('cogs.scrim_commands')
            await self.load_extension('cogs.admin_commands')
            await self.load_extension('cogs.stats_commands')
            await self.tree.sync()
        except Exception as e:
            print(f"Setup failed: {e}")
            raise


if __name__ == "__main__":
    bot = ScrimBot()
    bot.run(os.getenv("DISCORD_TOKEN"))

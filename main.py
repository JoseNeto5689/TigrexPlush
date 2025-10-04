
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import music_commands
import moderation_commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is online!")

music_commands.setup(bot)
moderation_commands.setup(bot)

bot.run(TOKEN)
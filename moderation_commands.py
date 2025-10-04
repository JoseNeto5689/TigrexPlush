import discord
from discord import app_commands
import asyncio

def setup(bot):
    @bot.tree.command(name="ritual", description="Summon the ritual")
    @app_commands.describe(user="Place the name of the user")
    async def ritual(interaction: discord.Interaction, user: discord.Member, times: int = 1):
        await interaction.response.send_message(f"Starting the ritual for {user.mention}!", ephemeral=True)
        for i in range(times):
            await interaction.channel.send(f"{user.mention}")
            await asyncio.sleep(2)
        
        await interaction.channel.send(f"Ritual completed!") 
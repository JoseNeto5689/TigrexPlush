import discord
from discord import app_commands
import asyncio
from datetime import datetime, timezone, timedelta

def setup(bot):
    @bot.tree.command(name="ritual", description="Summon the ritual")
    @app_commands.describe(user="Place the name of the user")
    async def ritual(interaction: discord.Interaction, user: discord.Member, times: int = 1):
        await interaction.response.send_message(f"Starting the ritual for {user.mention}!", ephemeral=True)
        for i in range(times):
            await interaction.channel.send(f"{user.mention}")
            await asyncio.sleep(2)
        
        await interaction.channel.send(f"Ritual completed!")


    @bot.tree.command(name="schedule", description="Register a scheduled message")
    @app_commands.describe(
        message="Message to be sent",
        date_time="Date and time in the format HH:MM DD-MM-YYYY"
    )
    async def schedule(interaction: discord.Interaction, message: str, date_time: str):
        try:
            brasilia = timezone(timedelta(hours=-3))
            
            target_time = datetime.strptime(date_time, "%H:%M %d-%m-%Y").replace(tzinfo=brasilia)

            now = datetime.now(brasilia)

            delay = (target_time - now).total_seconds()

            if delay <= 0:
                await interaction.response.send_message("❌ This date/time has already passed!", ephemeral=True)
                return

            await interaction.response.send_message(
                f"✅ Message scheduled for **{date_time}**!\n"
                f"Message: `{message}`", ephemeral=True
            )

            await asyncio.sleep(delay)

            await interaction.channel.send(message)

        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Use: `HH:MM DD-MM-YYYY`",
                ephemeral=True
            )

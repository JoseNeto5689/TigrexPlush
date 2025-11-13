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


    @bot.tree.command(name="schedule", description="Agenda uma mensagem para um horário específico")
    @app_commands.describe(
        message="Mensagem que será enviada",
        date_time="Data e horário no formato HH:MM DD-MM-YYYY"
    )
    async def schedule(interaction: discord.Interaction, message: str, date_time: str):
        try:
            brasilia = timezone(timedelta(hours=-3))
            
            target_time = datetime.strptime(date_time, "%H:%M %d-%m-%Y").replace(tzinfo=brasilia)

            now = datetime.now(brasilia)

            delay = (target_time - now).total_seconds()

            if delay <= 0:
                await interaction.response.send_message("❌ Essa data/hora já passou!", ephemeral=True)
                return

            await interaction.response.send_message(
                f"✅ Mensagem agendada para **{date_time}**!\n"
                f"Mensagem: `{message}`", ephemeral=True
            )

            await asyncio.sleep(delay)

            await interaction.channel.send(message)

        except ValueError:
            await interaction.response.send_message(
                "❌ Formato de data inválido! Use: `HH:MM DD-MM-YYYY`",
                ephemeral=True
            )

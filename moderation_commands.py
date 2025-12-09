import discord
from discord import app_commands
import asyncio
from datetime import datetime, timezone, timedelta
import ai
import random

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
            
            
    @bot.tree.command(name="ask", description="Ask a question to the Tigrex AI")
    @app_commands.describe(question="The question you want to ask")
    async def ask(interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        try:
            answer = ai.check_instructions(question)
            print(answer)
            
            if answer.get("function") == "ask_question":
                answer = ai.ask_question(answer.get("params")[0])
                await interaction.followup.send(answer)
                return
                
            elif answer.get("function") == "ritual":
                user_id = int(answer.get("params")[0])
                times = int(answer.get("params")[1])
                
                if times is None or times <= 0:
                    times = 1
                if not user_id:
                    await interaction.followup.send("❌ User not found in this server!")
                    return
                await interaction.followup.send(f"Starting the ritual for <@{user_id}>!")
                for i in range(times):
                    await interaction.channel.send(f"<@{user_id}>")
                    await asyncio.sleep(2)
                
                await interaction.channel.send(f"Ritual completed!")
                return
                
            elif answer.get("function") == "schedule_message":
                message_text = answer.get("params")[0]
                date_time = answer.get("params")[1]
                
                brasilia = timezone(timedelta(hours=-3))
                target_time = datetime.strptime(date_time, "%H:%M %d-%m-%Y").replace(tzinfo=brasilia)
                now = datetime.now(brasilia)
                delay = (target_time - now).total_seconds()
                if delay <= 0:
                    await interaction.followup.send("❌ This date/time has already passed!")
                    return
                await interaction.followup.send(
                    f"✅ Message scheduled for **{date_time}**!\n"
                    f"Message: `{message_text}`"
                )
                await asyncio.sleep(delay)
                await interaction.channel.send(message_text)    
                return
            
            elif answer.get("function") == "draw":
                min = int(answer.get("params")[0])
                max = int(answer.get("params")[1])
                
                result = random.randint(int(min), int(max))
                await interaction.followup.send(f"{result}")
                return
            else:
                return
            
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred while processing your request")
            return

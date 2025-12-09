import discord
from discord import app_commands
import asyncio
import os
from gtts import gTTS
import ai 

# --- Função adicionada ---
def limpar_mp3_antigos():
    for arquivo in os.listdir("."):
        if arquivo.endswith(".mp3"):
            try:
                os.remove(arquivo)
            except Exception as e:
                print(f"Erro ao remover {arquivo}: {e}")


async def join_channel(interaction: discord.Interaction, channel: discord.VoiceChannel):
    if interaction.guild.voice_client is not None:

        if interaction.guild.voice_client.channel == channel:
            return interaction.guild.voice_client

        else:
            await interaction.guild.voice_client.move_to(channel)
            return interaction.guild.voice_client
    else:
        return await channel.connect()

def setup(bot):
    @bot.tree.command(name="ask-voice", description="Faça uma pergunta e o Tigrex AI responderá por áudio")
    @app_commands.describe(question="A pergunta que você quer fazer")
    async def ask_voice(interaction: discord.Interaction, question: str):
        
        limpar_mp3_antigos()
        
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Você precisa estar em um canal de voz para usar este comando!", ephemeral=True)
            return

        user_channel = interaction.user.voice.channel
        
        await interaction.response.defer(thinking=True)

        try:

            voice_client = await join_channel(interaction, user_channel)

            resposta_texto = ai.ask_question(question)
            
            if not resposta_texto:
                resposta_texto = "Desculpe, não consegui gerar uma resposta."

            await interaction.followup.send(f"Gerando resposta...")


            tts = gTTS(text=resposta_texto, lang='pt', slow=False)
            arquivo_audio = f"temp_audio_{interaction.id}.mp3"
            tts.save(arquivo_audio)

            if voice_client.is_playing():
                voice_client.stop()
            
            source = discord.FFmpegPCMAudio(arquivo_audio, before_options='-filter_complex "afftfilt=real=\'hypot(re,im)*sin(0)\':imag=\'hypot(re,im)*cos(0)\':win_size=512:overlap=0.75"')
            voice_client.play(source)

            while voice_client.is_playing():
                await asyncio.sleep(1)

            if os.path.exists(arquivo_audio):
                os.remove(arquivo_audio)

        except Exception as e:
            await interaction.followup.send(f"Ocorreu um erro ao processar o áudio")
            if 'arquivo_audio' in locals() and os.path.exists(arquivo_audio):
                os.remove(arquivo_audio)
                
                
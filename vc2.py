import discord
from discord import app_commands
import asyncio
import os
import wave
from google import genai
from google.genai import types
import ai

# --- Configuração da API do Google ---
# Certifique-se de definir sua API KEY aqui ou nas variáveis de ambiente
os.environ["GOOGLE_API_KEY"] = "AIzaSyAQbjfc2hroDXROvowEbzgDDsU1h07nbp8" 

# Função auxiliar fornecida para salvar o arquivo WAV
def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

# Função para gerar o áudio com Gemini (roda em thread separada)
def generate_gemini_audio(question: str):
    client = genai.Client()
    
    # Prompt para garantir que ele responda e não apenas repita
    prompt_text = f"Responda a seguinte pergunta de forma clara e natural em português: {question}"

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts", # Usando o modelo especificado
        contents=prompt_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name='Zubenelgenubi', # Opções: 'Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede'
                    )
                )
            ),
        )
    )
    # Retorna os dados binários do áudio
    return response.candidates[0].content.parts[0].inline_data.data

# Função auxiliar para gerenciar conexão de voz
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
    @bot.tree.command(name="ask-voice", description="Pergunte ao Tigrex AI (Resposta com Áudio Nativo)")
    @app_commands.describe(question="A pergunta para a IA")
    async def ask_voice(interaction: discord.Interaction, question: str):
        
        # 1. Validação de canal de voz
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Entre em um canal de voz primeiro!", ephemeral=True)
            return

        user_channel = interaction.user.voice.channel
        
        # 2. Defer (Adiar resposta) pois geração de áudio leva tempo
        await interaction.response.defer(thinking=True)

        try:
            # 3. Conectar ao canal
            voice_client = await join_channel(interaction, user_channel)

            # Notifica o usuário que está processando
            await interaction.followup.send(f"🎙️ **Pergunta:** {question}\n*Gerando resposta de áudio")

            # 4. Gerar Áudio (Executando em thread para não bloquear o bot)
            # O Discord.py é async, mas a lib do Google é sync, então usamos to_thread
            
            text = ai.ask_question(question)
            print(text)
            
            pcm_data = await asyncio.to_thread(generate_gemini_audio, text)
            
            # 5. Salvar arquivo temporário
            filename = f"temp_response_{interaction.id}.wav"
            
            # Executa a função wave_file fornecida
            wave_file(filename, pcm_data)

            # 6. Tocar o áudio
            if voice_client.is_playing():
                voice_client.stop()

            source = discord.FFmpegPCMAudio(filename)
            voice_client.play(source)

            # Loop para esperar o áudio terminar antes de apagar o arquivo
            while voice_client.is_playing():
                await asyncio.sleep(1)

            # 7. Limpeza
            if os.path.exists(filename):
                os.remove(filename)

        except Exception as e:
            await interaction.followup.send(f"⚠️ Ocorreu um erro: {str(e)}")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)
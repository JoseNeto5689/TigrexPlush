import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
from dotenv import load_dotenv
import yt_dlp # NEW
from collections import deque # NEW
import asyncio # NEW
import re
from utils import get_video_info
from utils import LocalStorage
import recommendation

SONG_QUEUES = {}
actually_playing = {}
AUTOPLAY = {}

def is_url(text: str) -> bool:

    url_pattern = re.compile(
        r'^(https?:\/\/)?'              
        r'(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})'  
        r'(\/[^\s]*)?$'                 
    )
    return re.match(url_pattern, text) is not None

def setup(bot: commands.Bot):
    
    async def search_ytdlp_async(query, ydl_opts):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: _extract(query, ydl_opts))

    def _extract(query, ydl_opts):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)
    
    @bot.tree.command(name="skip", description="Skips the current playing song")
    async def skip(interaction: discord.Interaction):
        try:
            vc = interaction.guild.voice_client

            msg = ""
            if vc and (vc.is_playing() or vc.is_paused()):
                vc.stop()
                msg = "⏭️ Skipped the current song."
            else:
                msg = "❌ Not playing anything to skip."
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(msg)
                    return
            except Exception:
                pass

            try:
                await interaction.followup.send(msg)
                return
            except discord.errors.NotFound:
                pass 

            await interaction.channel.send(msg)

        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"⚠️ Error: {e}")
                    return
            except:
                pass

            try:
                await interaction.followup.send(f"⚠️ Error: {e}")
            except:
                await interaction.channel.send(f"⚠️ Error: {e}")



    @bot.tree.command(name="pause", description="Pause the currently playing song.")
    async def pause(interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            return await interaction.response.send_message("I'm not in a voice channel.")
        if not voice_client.is_playing():
            return await interaction.response.send_message("Nothing is currently playing.")
        voice_client.pause()
        await interaction.response.send_message("Playback paused!")


    @bot.tree.command(name="stop", description="Stop playback and clear the queue.")
    async def stop(interaction: discord.Interaction):        
        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return await interaction.response.send_message("I'm not connected to any voice channel.")

        guild_id_str = str(interaction.guild_id)
        if guild_id_str in SONG_QUEUES:
            SONG_QUEUES[guild_id_str].clear()
            
        actually_playing.pop(interaction.guild_id, None)
        
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        await interaction.response.send_message("Stopped playback and disconnected!")

        return await voice_client.disconnect()



    @bot.tree.command(name="play", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="Search query")
    async def play(interaction: discord.Interaction, song_query: str):
        audio_url = None
        title = None
        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None

        if voice_channel is None:
            await interaction.followup.send("You must be in a voice channel.")
            return

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        ydl_options = {
            "format": "bestaudio[abr<=96]/bestaudio",
            "noplaylist": True,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
            "quiet": True,
            "extractor_args": {"youtube": "player_client=mweb" },
        }
        
        if is_url(song_query):
            song_info = get_video_info(song_query)
            audio_url = song_info["url"]
            title = song_info["title"]
            
        if audio_url is None and title is None:
            results = []
            query = "ytsearch1: " + song_query
            for i in range(3): 
                try:
                    results = await search_ytdlp_async(query, ydl_options)
                    break
                except Exception as e:
                    await interaction.followup.send(f"Error fetching the song")
                    if i == 2: 
                        await interaction.followup.send(f"Youtube is dead or something else is wrong.")
                    return
            tracks = results.get("entries", [])

            if tracks is None:
                await interaction.followup.send("No results found.")
                return

            if len(tracks) == 0:
                await interaction.followup.send("No results found.")
                return

            first_track = tracks[0]
            audio_url = first_track["url"]
            title = first_track.get("title", "Untitled")

        actually_playing[interaction.guild_id] = {"audio_url": audio_url, "title": title, "webpage_url": first_track.get("webpage_url", None)}
        guild_id = str(interaction.guild_id)
        if SONG_QUEUES.get(guild_id) is None:
            SONG_QUEUES[guild_id] = deque()

        SONG_QUEUES[guild_id].append((audio_url, title, actually_playing[interaction.guild_id].get("webpage_url", None)))

        if voice_client.is_playing() or voice_client.is_paused():
            await interaction.followup.send(f"Added to queue: **{title}**")
        else:
            await interaction.followup.send(f"Now playing: **{title}**")
            await play_next_song(voice_client, guild_id, interaction.channel)


    async def play_next_song(voice_client, guild_id, channel):
        if SONG_QUEUES[guild_id]:
            audio_url, title, webpage_url = SONG_QUEUES[guild_id].popleft()
            actually_playing[int(guild_id)] = {"audio_url": audio_url, "title": title, "webpage_url": webpage_url}

            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",
            }

            source = discord.FFmpegOpusAudio(audio_url, **ffmpeg_options)

            def after_play(error):
                if error:
                    print(f"Error playing {title}: {error}")
                asyncio.run_coroutine_threadsafe(play_next_song(voice_client, guild_id, channel), bot.loop)

            voice_client.play(source, after=after_play)
        else:
            if AUTOPLAY.get(int(guild_id), True):
                current = actually_playing.get(int(guild_id), None)
                if current:
                    next_song = recommendation.get_youtube_recommendations(current["webpage_url"])
                    print(next_song)
                    song_info = get_video_info(next_song["url"])
                    audio_url = song_info["url"]
                    title = song_info["title"]  
                    actually_playing[int(guild_id)] = {"audio_url": audio_url, "title": title, "webpage_url": song_info.get("webpage_url", None)}
                    SONG_QUEUES[guild_id].append((audio_url, title, next_song["url"]))
                    await channel.send(f"Autoplaying next song: **{title}**")
                    await play_next_song(voice_client, guild_id, channel)
                    return
                    

            await voice_client.disconnect()
            SONG_QUEUES[guild_id] = deque()

    @bot.tree.command(name="select", description="Play a song or add it to the queue.")
    @app_commands.describe(song_query="Search query")
    async def select(interaction: discord.Interaction, song_query: str):
        await interaction.response.defer()

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None

        if voice_channel is None:
            await interaction.followup.send("You must be in a voice channel.")
            return

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        ydl_options = {
            "format": "bestaudio[abr<=96]/bestaudio",
            "noplaylist": True,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
            "quiet": True,
            "extractor_args": {"youtube": "player_client=mweb" },
        }
        
        query = "ytsearch5: " + song_query
        for i in range(3):
            try:
                results = await search_ytdlp_async(query, ydl_options)
                break
            except Exception as e:
                await interaction.followup.send(f"Error fetching the song")
                if i == 2: 
                    await interaction.followup.send(f"Youtube is dead or something else is wrong.")
                return
        tracks = results.get("entries", [])

        if tracks is None:
            await interaction.followup.send("No results found.")
            return

        if len(tracks) == 0:
            await interaction.followup.send("No results found.")
            return

        
        first_five = tracks[:5]
        options = [discord.SelectOption(label=track.get("title", "Untitled"), value=index) for index, track in enumerate(first_five)]
        
        
        class MyView(discord.ui.View):
            @discord.ui.select(
                placeholder = "Choose a song",
                options = options
        )
            async def select_callback(self, interaction_local, select):

                voice_channel = interaction_local.user.voice.channel if interaction_local.user.voice else None

                if voice_channel is None:
                    await interaction_local.followup.send("You must be in a voice channel.")
                    return

                voice_client = interaction_local.guild.voice_client

                if voice_client is None:
                    voice_client = await voice_channel.connect()
                elif voice_channel != voice_client.channel:
                    await voice_client.move_to(voice_channel)
                
                selected_index = int(select.values[0])
                selected_track = first_five[selected_index] if 0 <= selected_index < len(first_five) else None
                if selected_track:
                    audio_url = selected_track["url"]
                    title = selected_track.get("title", "Untitled")

                    actually_playing[interaction.guild_id] = {"audio_url": audio_url, "title": title, "webpage_url": selected_track.get("webpage_url", None)}

                    guild_id = str(interaction.guild_id)
                    if SONG_QUEUES.get(guild_id) is None:
                        SONG_QUEUES[guild_id] = deque()

                    SONG_QUEUES[guild_id].append((audio_url, title, actually_playing[interaction.guild_id].get("webpage_url", None)))

                    if voice_client.is_playing() or voice_client.is_paused():
                        await interaction_local.response.send_message(f"Added to queue: **{title}**")
                    else:
                        await interaction_local.response.send_message(f"Now playing: **{title}**")
                        return await play_next_song(voice_client, guild_id, interaction_local.channel)
                        
                else:
                    return await interaction_local.response.send_message("Selected track not found.")

        await interaction.followup.send("Choose your favorite song:", view=MyView(), ephemeral=True)
        
        
    """
    @bot.tree.command(name="autoplay", description="Toggle autoplay mode.")
    @app_commands.describe(mode="Choose 'on' or 'off'")
    async def autoplay(interaction: discord.Interaction, mode: str):
        mode = mode.lower()
        if mode not in ("on", "off"):
            return await interaction.response.send_message("Use: /autoplay on ou /autoplay off.")

        guild_id = interaction.guild_id

        AUTOPLAY[guild_id] = (mode == "on")

        await interaction.response.send_message(
            f"Autoplay **{mode.upper()}**!"
        )    


    @bot.tree.command(name="playlist-create", description="Manage your playlist.")
    @app_commands.describe(playlist_name="Choose a playlist name")
    async def create_playlist(interaction: discord.Interaction, playlist_name: str):
        storage = LocalStorage()
        if storage.get_item(playlist_name) is not None:
            return await interaction.response.send_message(f"Playlist '{playlist_name}' already exists.")
        storage.set_item(playlist_name, [])
        await interaction.response.send_message(f"Playlist '{playlist_name}' created!")
        
    
    @bot.tree.command(name="playlist-add", description="Manage your playlist.")
    @app_commands.describe(playlist_name="Find a playlist name")
    async def add_to_playlist(interaction: discord.Interaction, playlist_name: str):
        storage = LocalStorage()
        if storage.get_item(playlist_name) is None:
            return await interaction.response.send_message(f"Playlist '{playlist_name}' does not exist.")
        
        if actually_playing == {}:
            return await interaction.response.send_message("No song is currently playing.")
        playlist = storage.get_item(playlist_name)

        playlist.append(actually_playing[interaction.guild_id])
        storage.set_item(playlist_name, playlist)
        await interaction.response.send_message(f"Added '{actually_playing[interaction.guild_id]['title']}' to playlist '{playlist_name}'!")
        
    @bot.tree.command(name="playlist-play", description="Manage your playlist.")
    @app_commands.describe(playlist_name="Find a playlist name")
    async def play_playlist(interaction: discord.Interaction, playlist_name: str):
        await interaction.response.send_message("Processing your playlist...")
        storage = LocalStorage()
        if storage.get_item(playlist_name) is None:
            return await interaction.followup.send(f"Playlist '{playlist_name}' does not exist.")
        
        playlist = storage.get_item(playlist_name)
        if len(playlist) == 0:
            return await interaction.followup.send(f"Playlist '{playlist_name}' is empty.")

        voice_channel = interaction.user.voice.channel if interaction.user.voice else None

        if voice_channel is None:
            await interaction.followup.send("You must be in a voice channel.")
            return

        voice_client = interaction.guild.voice_client

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_channel != voice_client.channel:
            await voice_client.move_to(voice_channel)

        guild_id = str(interaction.guild_id)
        if SONG_QUEUES.get(guild_id) is None:
            SONG_QUEUES[guild_id] = deque()

        for song in playlist:
            song_info = get_video_info(song.get("webpage_url"))
            audio_url = song_info["url"]
            SONG_QUEUES[guild_id].append((audio_url, song.get("title", "Untitled"), song.get("webpage_url", None)))

        if voice_client.is_playing() or voice_client.is_paused():
            await interaction.response.send_message(f"Added playlist '{playlist_name}' to the queue.")
        else:
            await interaction.followup.send(f"Now playing playlist '{playlist_name}'!")
            await play_next_song(voice_client, guild_id, interaction.channel)

    @bot.tree.command(name="playlist-delete", description="Manage your playlist.")
    @app_commands.describe(playlist_name="Find a playlist name")
    async def remove_playlist(interaction: discord.Interaction, playlist_name: str):
        storage = LocalStorage()
        if storage.get_item(playlist_name) is None:
            return await interaction.response.send_message(f"Playlist '{playlist_name}' does not exist.")

        storage.remove_item(playlist_name)
        await interaction.response.send_message(f"Removed playlist '{playlist_name}'.")
        
    @bot.tree.command(name="playlists", description="List all playlists.")
    async def list_playlists(interaction: discord.Interaction):
        storage = LocalStorage()
        playlists = storage.keys()
        if not playlists:
            return await interaction.response.send_message("No playlists found.")
        playlist_list = "\n".join(playlists)
        await interaction.response.send_message(f"Playlists:\n{playlist_list}")

    @bot.tree.command(name="last_played", description="Shows the last played song.")
    async def last_played(interaction: discord.Interaction):
        if interaction.guild_id not in actually_playing:
            return await interaction.response.send_message("No song has been played yet.")
        current = actually_playing[interaction.guild_id]
        await interaction.response.send_message(f"Last played: **{current['title']}**")
    
    @bot.tree.command(name="playlist-pop", description="Delete the last song added to the playlist.")
    @app_commands.describe(playlist_name="Find a playlist name")
    async def pop_from_playlist(interaction: discord.Interaction, playlist_name: str):
        storage = LocalStorage()
        if storage.get_item(playlist_name) is None:
            return await interaction.response.send_message(f"Playlist '{playlist_name}' does not exist.")
        
        playlist = storage.get_item(playlist_name)
        if len(playlist) == 0:
            return await interaction.response.send_message(f"Playlist '{playlist_name}' is empty.")
        
        removed_song = playlist.pop()
        storage.set_item(playlist_name, playlist)
        await interaction.response.send_message(f"Removed '{removed_song['title']}' from playlist '{playlist_name}'!")
        
    
    @bot.tree.command(name="resume", description="Resume the currently paused song.")
    async def resume(interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client

        if voice_client is None:
            return await interaction.response.send_message("I'm not in a voice channel.")

        if not voice_client.is_paused():
            return await interaction.response.send_message("I’m not paused right now.")
        
        voice_client.resume()
        await interaction.response.send_message("Playback resumed!")
        
    """
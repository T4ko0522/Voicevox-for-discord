import discord
from discord import FFmpegPCMAudio, app_commands
from discord import Embed
import discord.opus
from dotenv import load_dotenv
import requests
import json
import asyncio
import os
import re
from datetime import datetime
discord.opus.load_opus('/opt/homebrew/Cellar/opus/1.5.2/lib/libopus.0.dylib')
load_dotenv('.env')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

client = discord.Client(intents=intents, activity=discord.Game("Voicevoxで読み上げ中"))
tree = app_commands.CommandTree(client)

TOKEN = os.getenv('VoicevoxBotTOKEN') 
VOICEVOX_API_URL = 'http://localhost:50021'
DICTIONARY_FILE = 'temporary/dictionary.json'
FFMPEG_PATH = '/opt/homebrew/bin/ffmpeg'


@client.event
async def on_ready():
    await tree.sync()
    print(f'┎-------------------------------┒\n┃      login is successful      ┃\n┃    logged in {client.user}    ┃\n┖-------------------------------┚ ')

def load_dictionary():
    if os.path.exists(DICTIONARY_FILE):
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_dictionary(dictionary):
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=4)
dictionary = load_dictionary()

def shorten_urls(message: str) -> str:
    url_pattern = re.compile(r'(https?://\S+)')
    return url_pattern.sub('[URL省略]', message)

def apply_dictionary(message: str, dictionary: dict) -> str:
    for word, reading in dictionary.items():
        message = message.replace(word, reading)
    return message

async def generate_voice(text: str, speaker: int = 1):
    params = {
        "text": text,
        "speaker": speaker
    }
    response = requests.post(f"{VOICEVOX_API_URL}/audio_query", params=params)
    audio_query = response.json()
    response = requests.post(f"{VOICEVOX_API_URL}/synthesis", params=params, data=json.dumps(audio_query))
    save_path = "temporary/voice.mp3" 
    with open(save_path, "wb") as f:
        f.write(response.content)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.guild.voice_client is None:
        return
    #URLを省略
    message_content = shorten_urls(message.content)
    #辞書変換
    converted_message = apply_dictionary(message_content, dictionary)
    await generate_voice(converted_message)
    voice_client = message.guild.voice_client
    audio_source = FFmpegPCMAudio("temporary/voice.mp3", executable=FFMPEG_PATH)
    if not voice_client.is_playing():
        #再生
        voice_client.play(audio_source)

async def check_voice_channel_members(voice_client, text_channel):
    connected_time = datetime.now()
    voice_channel_name = voice_client.channel.name

    while True:
        members = voice_client.channel.members
        if len(members) <= 1:
            disconnected_time = datetime.now()
            duration = disconnected_time - connected_time
            embed = Embed(
                title="ボイスチャンネルから切断しました",
                color=discord.Color.red()
            )
            embed.add_field(name="接続していたボイスチャンネル", value=voice_channel_name, inline=False)
            embed.add_field(name="接続時間", value=connected_time.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed.add_field(name="切断時間", value=disconnected_time.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed.add_field(name="接続していた時間", value=str(duration), inline=False)
            
            await text_channel.send(embed=embed)
            await voice_client.disconnect()
            break
        await asyncio.sleep(2)

@tree.command(name="join", description="ボイスチャンネルに接続する。")
async def join(interaction: discord.Interaction):
    voice_state = interaction.user.voice
    if voice_state and voice_state.channel:
        if interaction.guild.voice_client is not None:
            embed = Embed(
                title="エラー",
                description="既にボイスチャットに接続されています。",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        voice_channel = voice_state.channel
        vc = await voice_channel.connect()
        
        channel_name = voice_channel.name
        connected_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        member_count = len(voice_channel.members)
        embed = Embed(
            title="ボイスチャンネルに接続しました",
            color=discord.Color.green()
        )
        embed.add_field(name="接続したチャンネル", value=channel_name, inline=False)
        embed.add_field(name="コマンドが入力されたチャンネル", value=interaction.channel.name, inline=False)
        embed.add_field(name="接続時のボイスチャットにいる人数", value=f"{member_count} 人", inline=False)
        embed.add_field(name="接続時の時間", value=connected_time, inline=False)

        await interaction.response.send_message(embed=embed)
        await check_voice_channel_members(vc, interaction.channel)
    else:
        embed = Embed(
            title="エラー",
            description="ボイスチャンネルに接続してからもう一度お試しください。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)


@tree.command(name="dissconect", description="ボイスチャットから切断します。")
async def leave(interaction: discord.Interaction):
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    if voice_client:
        await voice_client.disconnect()
        embed = Embed(
            title="切断しました",
            description="ボイスチャットから切断しました。:wave:",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = Embed(
            title="エラー",
            description="ボイスチャットに接続していません。:no_entry_sign:",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)


@tree.command(name="dictionary_register", description="単語の読み方を登録します。")
async def dictionary_register(interaction: discord.Interaction, word: str, reading: str):
    dictionary[word] = reading
    save_dictionary(dictionary)
    embed = Embed(
        title="辞書に登録完了",
        description=f"単語 '{word}' を読み方 '{reading}' として登録しました。",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)


@tree.command(name="dictionary_delete", description="登録してある単語を削除します。")
async def dictionary_remove(interaction: discord.Interaction, word: str):
    if word in dictionary:
        del dictionary[word]
        save_dictionary(dictionary)
        embed = Embed(
            title="辞書から削除完了",
            description=f"単語 '{word}' の読み方を辞書から削除しました。",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = Embed(
            title="エラー",
            description=f"単語 '{word}' は辞書に登録されていません。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)


@tree.command(name="help", description="コマンドリストを表示します。")
async def help_command(interaction: discord.Interaction):
    embed = Embed(
        title="コマンド一覧",
        description="使用できるコマンドのリストです。",
        color=discord.Color.blue()
    )
    embed.add_field(name="/join", value="指定されたボイスチャンネルに参加します。", inline=False)
    embed.add_field(name="/dissconnect", value="ボイスチャンネルから退出します。", inline=False)
    embed.add_field(name="/dictionary_register", value="単語の読み方を登録します。", inline=False)
    embed.add_field(name="/dictionary_delete", value="登録してある単語を削除します。", inline=False)
    embed.add_field(name="/help", value="このヘルプメッセージを表示します。", inline=False)
    embed.add_field(
        name="問い合わせ先", 
        value="[Twitter: @Tako_0522](https://x.com/Tako_0522)", 
        inline=False
    )

    await interaction.response.send_message(embed=embed)


client.run(TOKEN)

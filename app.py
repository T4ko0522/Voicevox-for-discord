# Beta v0.2 released
import discord
from discord import FFmpegPCMAudio, app_commands
import discord.opus
#from dotenv import load_dotenv  # .envを使用する場合はコメントアウトを消してください。
import requests
import json
import asyncio
import os
import re

discord.opus.load_opus('/opt/homebrew/Cellar/opus/1.5.2/lib/libopus.0.dylib')  # 環境によってパスが異なる場合があります。
#load_dotenv('')  # dotenvを使用してtokenを利用する場合は、ここに.envファイルのパスを指定してください。

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

client = discord.Client(intents=intents, activity=discord.Game("Voicevoxで読み上げ中"))
tree = app_commands.CommandTree(client)
#TOKEN = os.getenv('VoicevoxBotTOKEN')# .envからtokenを読み込む場合
TOKEN = ("MTIxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")  
VOICEVOX_API_URL = 'http://localhost:50021'
DICTIONARY_FILE = '　/dictionary.json'  # dictionaryファイルのパスを指定してください。
FFMPEG_PATH = '/opt/homebrew/bin//ffmpeg'  # 環境によってパスが異なる場合があります。

# 起動とtree同期
@client.event
async def on_ready():
    print("┎--------------------┒\n┃login is successful ┃\n┖--------------------┚")
    await tree.sync()

# 辞書の読み込み
def load_dictionary():
    if os.path.exists(DICTIONARY_FILE):
        with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# 辞書の保存
def save_dictionary(dictionary):
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=4)

dictionary = load_dictionary()

# URLを省略する関数
def shorten_urls(message: str) -> str:
    url_pattern = re.compile(r'(https?://\S+)')
    return url_pattern.sub('[URL省略]', message)

# joinコマンド
@tree.command(name="join", description="ボイスチャンネルに接続する。")
async def join(interaction: discord.Interaction):
    voice_state = interaction.user.voice
    if voice_state and voice_state.channel:
        # エラー：既に参加している場合
        if interaction.guild.voice_client is not None:
            await interaction.response.send_message(":no_entry_sign:既にボイスチャットに接続されています。:no_entry_sign:")
            return
        voice_channel = voice_state.channel
        # 接続
        vc = await voice_channel.connect()
        await interaction.response.send_message('やほ〜:saluting_face:')
        await check_voice_channel_members(vc, interaction.channel)
    else:
        # エラー：ボイスチャンネルに参加していない場合
        await interaction.response.send_message(":no_entry_sign:ボイスチャンネルに接続してからもう一度お試しください。:no_entry_sign:")

# ボイスチャンネルに誰もいなくなったら自動で切断する
async def check_voice_channel_members(voice_client, text_channel):
    while True:
        members = voice_client.channel.members
        if len(members) <= 1:
            await text_channel.send("ばいば〜い:innocent:")
            await voice_client.disconnect()
            break
        # 2秒おきにメンバーの数を確認
        await asyncio.sleep(2)

# 辞書変換
def apply_dictionary(message: str, dictionary: dict) -> str:
    for word, reading in dictionary.items():
        message = message.replace(word, reading)
    return message

# 読み上げ用のボイスを作成
async def generate_voice(text: str, speaker: int = 1):
    params = {
        "text": text,
        "speaker": speaker
    }
    response = requests.post(f"{VOICEVOX_API_URL}/audio_query", params=params)
    audio_query = response.json()

    response = requests.post(f"{VOICEVOX_API_URL}/synthesis", params=params, data=json.dumps(audio_query))
    # 保存先
    save_path = "/Users/XXXX/Project/読み上げ/temporary/voice.mp3"  # これは例の保存先です。
    
    with open(save_path, "wb") as f:
        f.write(response.content)

# メッセージ読み上げ
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.guild.voice_client is None:
        return
    # URLを省略
    message_content = shorten_urls(message.content)
    # 辞書変換
    converted_message = apply_dictionary(message_content, dictionary)
    await generate_voice(converted_message)
    voice_client = message.guild.voice_client
    audio_source = FFmpegPCMAudio("/Users/tako/Desktop/VSCode/読み上げ/temporary/voice.mp3", executable=FFMPEG_PATH)  # 99行目で指定したパスを指定してください。
    if not voice_client.is_playing():
        # 再生
        voice_client.play(audio_source)

# disconnectコマンド
@tree.command(name="dissconect", description="ボイスチャットから切断します。")
async def leave(interaction: discord.Interaction):
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    if voice_client:
        # 切断
        await voice_client.disconnect()
        await interaction.response.send_message('切断します:wave:')
    else:
        # エラー：ボイスチャンネルに接続していない場合
        await interaction.response.send_message(':no_entry_sign:ボイスチャットに接続してからもう一度お試しください。:no_entry_sign:')

# 辞書登録コマンド
@tree.command(name="dictionary_register", description="単語の読み方を登録します。")
async def dictionary_register(interaction: discord.Interaction, word: str, reading: str):
    dictionary[word] = reading
    save_dictionary(dictionary)
    await interaction.response.send_message(f"単語 '{word}' を読み方 '{reading}' として登録しました。")

# 辞書削除コマンド
@tree.command(name="dictionary_delete", description="登録してある単語を削除します。")
async def dictionary_remove(interaction: discord.Interaction, word: str):
    if word in dictionary:
        del dictionary[word]
        save_dictionary(dictionary)
        await interaction.response.send_message(f"単語 {word} の読み方を辞書から削除しました。")
    else:
        await interaction.response.send_message(f"単語 {word} は辞書に登録されていません。")

# helpコマンド
@tree.command(name="help", description="コマンドリストを表示します。")
async def help_command(interaction: discord.Interaction):
    # 表示するhelpメッセージ
    help_message = (
        "コマンド一覧:\n"
        "/join - 指定されたボイスチャンネルに参加します。\n"
        "/dissconnect - ボイスチャンネルから退出します。\n"
        "/dictionary_register - 単語の読み方を登録します。\n"
        "/dictionary_delete - 登録してある単語を削除します。\n"
        "/help - このヘルプメッセージを表示します。\n\n"
        "問い合わせ先\n"
        "Discord tako._.v\n"
        "Twitter Endroll_ow\n"
    )
    await interaction.response.send_message(help_message)

# 起動
client.run(TOKEN)

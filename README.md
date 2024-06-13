Voicevox apiを利用したdiscordの読み上げbot (改善の余地あり)

*ここに公開されているT4jkoが作成した読み上げbotのコードは、個人使用の範囲内での改変は自由ですが、二次配布や自作発言などは一切を禁止します。

動作確認
MacBookAir M1 macOS Sonoma ver 14.5 Python3.11.7

インストール、ダウンロードが必要なアプリ、モジュール
discord.py 2.3.2 (discordで音声関連のライブラリをインストールするのにはpip install "discord.py[voice]"を利用すると楽です。)
anyio
requests
json
dotenv(どちらでも)
FFmpeg
Opus
os
re

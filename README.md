# Discord チャンネル全件テキスト抽出 Bot (Python)

このリポジトリには、Discord サーバー内のテキストチャンネル履歴を `.txt` に書き出す Bot があります。

## できること

- `!export_all` コマンドで、実行したサーバーの全テキストチャンネルを抽出
- チャンネル名と同じフォルダを作成し、投稿ごとに 1 テキストファイルを出力
- メッセージ本文、添付ファイル URL、Embed の基本情報を保存
- 投稿本文がリンクのみの場合はリンク先HTMLをMarkdown化して保存し、ページ内の画像/動画リンクをダウンロード

## セットアップ

1. 依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Discord Developer Portal で Bot を作成
   - `MESSAGE CONTENT INTENT` を有効化
   - サーバーに招待（最低でも対象チャンネルの閲覧履歴権限が必要）

3. 環境変数を設定

```bash
export DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN"
export COMMAND_PREFIX="!"
# 任意
export EXPORT_OUTPUT_DIR="exports"
```

4. 起動

```bash
python discord_export_bot.py
```

## 使い方

- Discord サーバー内で管理者権限を持つユーザーが以下を実行:

```text
!export_all
```

- 抽出結果は次の構造で保存されます。

```text
exports/
  <guild_id>_<guild_name>/
    <channel_name>/
      <timestamp>_<message_id>.txt
```


## リンクのみ投稿の追加保存

- 投稿本文が `https://...` のみだった場合、同名の `.md` ファイルを追加生成します。
- `.md` にはリンク先ページの本文をMarkdown変換した内容を保存します（HTMLページのみ）。
- ページ内の画像/動画リンク（`img`, `video`, `source`）は投稿ファイルと同名のフォルダへ保存します。

## 注意点

- Bot が読めるチャンネルのみ抽出されます。
- 大規模サーバーでは完了まで時間がかかります。
- API レート制限緩和のため、チャンネル間に短い待機を入れています。

# discord-extractor

Discord チャンネルの投稿を **Markdown 形式でエクスポート**する Bot です。
単なる本文保存だけでなく、投稿内リンク（X / YouTube / 通常ページ）の内容取得や、添付・埋め込み情報の記録にも対応しています。

---

## 1. できること

この Bot は、実行した**現在のチャンネル**を対象に投稿をエクスポートします。

- `/export_all`
  - 現在のチャンネル履歴を先頭から順に読み取り、1投稿 = 1ファイルで `.md` 出力
  - 投稿本文 + リンク展開結果 + embed / attachment 情報を保存
- `/count_up`
  - 現在チャンネルの投稿数を数えて、処理時間の目安を表示
- `/delete_all`
  - 現在チャンネルのメッセージを全削除（確認ボタンあり）
- `/delete_cmd`
  - Bot 投稿を削除

> 注意: コマンドはいずれも管理者権限が必要です。

---

## 2. 必要環境

- Python 3.12+
- ffmpeg（動画ダウンロード時に使用）
- Playwright のブラウザ実体（Chromium / Firefox）

このリポジトリは `pyproject.toml` ベースです。`uv` または `pip` でセットアップできます。

---

## 3. セットアップ

### A. `uv` を使う（推奨）

```bash
uv sync
uv run playwright install chromium firefox
```

### B. `venv + pip` を使う

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m playwright install chromium firefox
```

---

## 4. Discord 側の準備

1. Discord Developer Portal で Bot を作成
2. 以下を有効化
   - `MESSAGE CONTENT INTENT`
3. サーバーへ Bot を招待
4. Bot に対象チャンネルの閲覧権限・履歴閲覧権限を付与

---

## 5. 環境変数

起動前に次を設定してください。

```bash
export DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN"
export GUILD_ID="123456789012345678"
# 任意（未指定時は discord_exports）
export EXPORT_OUTPUT_DIR="discord_exports"
```

- `DISCORD_BOT_TOKEN`（必須）: Bot トークン
- `GUILD_ID`（必須）: スラッシュコマンド同期先サーバーID
- `EXPORT_OUTPUT_DIR`（任意）: 出力先ディレクトリ

> `COMMAND_PREFIX` は現行コードでは使っていません（スラッシュコマンドのみ）。

---

## 6. 起動方法

### `uv` の場合

```bash
uv run python discord_export_bot.py
```

### `venv + pip` の場合

```bash
python discord_export_bot.py
```

起動後、Bot がログインするとスラッシュコマンドが対象 Guild に同期されます。

---

## 7. 使い方（わかりやすく）

### Step 1: エクスポートしたいチャンネルを開く

Bot を入れたサーバーで、保存したいテキストチャンネルを開きます。

### Step 2: まず投稿数を確認（任意）

`/count_up` を実行すると、

- チャンネル投稿数
- 概算時間

を確認できます。

### Step 3: エクスポート実行

`/export_all` を実行します。

- Bot は投稿を古い順に処理します
- Bot 本人の投稿はスキップします
- 処理中は進捗メッセージを送信します（50件ごと）

### Step 4: 出力を確認

デフォルトでは次のように保存されます。

```text
discord_exports/
  <guild_name>_<guild_id>/
    <channel_name>/
      <timestamp>_<message_id>.md
      <timestamp>_<message_id>-media/
```

---

## 8. 出力内容の詳細

各 `.md` にはおおむね次が含まれます。

- `## content`
  - 投稿本文
- `### links`
  - 本文内 URL の展開結果
  - `x.com`: 投稿本文抽出 + 画像保存 + 動画取得（可能な場合）
  - `youtube.com`: yt-dlp で動画ダウンロード
  - その他 URL: ページ HTML を Markdown 化（`text/*`）
- `## embeds`
  - Embed タイトル/説明、proxy URL（image/video/thumbnail）
- `## attachments`
  - 添付ファイル URL

---

## 9. 運用時の注意点

- 大量投稿チャンネルは非常に時間がかかります（外部リンク取得の待機処理あり）。
- 外部サイト側の仕様変更・ログイン制限でリンク展開が失敗する場合があります。
- `/delete_all` は破壊的操作です。テストサーバーで挙動確認してから使ってください。
- Discord API の権限不足時は対象チャンネルを処理できません。

---

## 10. トラブルシュート

- `RuntimeError: DISCORD_BOT_TOKEN is not set`
  - `DISCORD_BOT_TOKEN` 未設定です
- 起動するがコマンドが出ない
  - `GUILD_ID` が誤っている可能性
  - Bot を対象サーバーに招待できているか確認
- Playwright 関連エラー
  - `python -m playwright install chromium firefox` を実行
- 動画取得失敗
  - `ffmpeg` の導入と PATH を確認

from playwright.async_api import async_playwright
import asyncio
import time
import random
import datetime as dt
import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from pathlib import Path
from urlextract import URLExtract
import discord
from discord.ext import commands
from markdownify import markdownify
import yt_dlp

import xcom_extractor

load_dotenv()
CMD_SET = ["!export_all", "!count_up", "!delete_all", "!delete_cmd"]
MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".mp4",
    ".webm",
    ".mov",
    ".mkv",
}
REQUEST_TIMEOUT = 20

# m3u8_url = "https://video.twimg.com/.../playlist.m3u8"
# download via yt-dlp


def sanitize_filename(name: str) -> str:
    """Create a filesystem-safe filename from a name."""
    name = name.replace("/", "-")
    name = name.replace("?", "_")
    name = name.replace("<", "_")
    name = name.replace(">", "_")
    name = name.replace("\\", "_")
    name = name.replace(":", "_")
    name = name.replace("*", "_")
    name = name.replace("|", "_")
    name = name.replace('"', "_")
    return name


def extract_msg_field(msg: discord.Message) -> str:
    """
    embedとattachmentを処理する
    embedはバックアップ用途(Xのポストなどが消えてもCDNにキャッシュが残るため)なのでproxy_urlを保存するようにする
    出力はmarkdown、H2
    """

    content = ""

    embed_lines = []
    if msg.embeds:
        content = "\n## embeds\n\n"
    for embed in msg.embeds:
        if embed:
            title = embed.title
            description = embed.description
            embed_content = f"### {title}\n\n{description}\n"
            if embed.thumbnail is not None:
                embed_content += f"[cached thumbnail]({embed.thumbnail.proxy_url})\n"
            if embed.image is not None:
                embed_content += f"[cached image]({embed.image.proxy_url})\n"
            if embed.video is not None:
                embed_content += f"[cached video]({embed.video.proxy_url})\n"
            if embed.fields is not None:
                print(embed.fields)

            # import json
            # print(f"DEBUG: {json.dumps(embed.to_dict())}")
            embed_lines.append(embed_content)

    attachment_lines = [f"attachment: <{a.url}>\n" for a in msg.attachments]
    if attachment_lines:
        content += "## attachments\n".join(attachment_lines, "\n")

    return content


def message_filename(message: discord.Message) -> str:
    ts = message.created_at.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ts}_{message.id}"


async def fetch_normal_url_as_md(url: str, media_path: Path) -> str:
    print(f"normal url: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )

        page = await context.new_page()
        res = await page.goto(url, timeout=60000, wait_until="load")
        time.sleep(10)
        content_type = res.header_value("content-type")

        print(f"DEBUG2: {url} @ {content_type}")

        if content_type.startswith("text/"):
            content = await page.content()
            md = markdownify(content, heading_style="ATX", default_title=True)
        elif content_type.startswith("image/") or content_type.startswith("video/"):
            ext = content_type.replace("image/").replace("video/")
            base_name = os.path.basename(url)[0:100]
            file_name = media_path / (f"{base_name}.{ext}")
            with open(file_name, "wb") as f:
                f.write(res.body())
            md = f"[url]({file_name})\n"
        else:
            raise Exception(f"Not handling content_type! {content_type}@{url}")

    return md


async def fetch_xcom_as_md(url: str, media_path: Path) -> str:
    print(f"X: {url}")
    content = await xcom_extractor.xcom_extract(url, media_path)
    return markdownify(content, heading_style="ATX", default_title=True)


def fetch_youtube_as_md(url: str, media_path: Path) -> str:
    print(f"youtube: {url}")
    media_path.mkdir(parents=True, exist_ok=True)
    ydl_opt = {
        "outtmpl": f"{media_path}/%(title).150B.%(ext)s",
        "ffmpeg_location": "/usr/bin/ffmpeg",
        "format": "bestvideo+bestaudio/best",
        "break_on_reject": True,
        "sleep_interval": 3,
        "max_sleep_interval": 5,
    }
    output = ""
    with yt_dlp.YoutubeDL(ydl_opt) as y:
        retcode = y.download([url])
        if retcode != 0:
            raise Exception(f"cannot download video: {url}")
        output = y.prepare_filename(y.extract_info(url, download=True))

    return f"<{url}>\n\n![[{output}]]"


async def fetch_url_as_md(urls: list(str), media_path: Path) -> str:
    """
    linkのリストを受け取って処理して返す、Hは気にしない
    """

    md = ""
    for url in urls:
        md += f"#### <{url}>"
        match urlparse(url).netloc:
            case "x.com":
                md += await fetch_xcom_as_md(url, media_path) + "\n"
                time.sleep(12 + random.randint(0, 3))
            case "youtube.com":
                md += await fetch_youtube_as_md(url, media_path) + "\n"
            case _:
                md += await fetch_normal_url_as_md(url, media_path) + "\n"
        time.sleep(3 + random.randint(0, 3))

    return md


async def msg_to_md(msg: discord.Message, media_path: Path) -> str:
    """
    contentにURLが含まれている場合、それをmarkdownに展開して読み込む
    markdownに変換するのはfetch_url_as_mdで
    """

    content = f"# {msg.id}\n\n"
    content = "## content\n\n"
    content += msg.content + "\n"
    extractor = URLExtract()
    links = extractor.find_urls(msg.content)
    links = list(set(links))

    if links:
        try:
            markdown = await fetch_url_as_md(links, media_path)
        except Exception as e:
            print(f"fetch: Error @ {links}, {e}")
            markdown = f"fetch error: {links}"
        content += f"\n### links\n\n{markdown}\n"

    content += extract_msg_field(msg)

    return content


async def export_channel(channel: discord.Channel, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    message_count = 0

    channel_dir = output_dir / sanitize_filename(channel.name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    try:
        async for msg in channel.history(limit=None, oldest_first=True):
            if any([cmd in msg.content for cmd in CMD_SET]) or msg.author.bot:
                print("skip  bot or cammand message")
                continue
            output_filename = channel_dir / (message_filename(msg) + ".md")
            media_path = channel_dir / (message_filename(msg) + "-media")

            content = await msg_to_md(msg, media_path)
            with output_filename.open("w", encoding="utf-8") as f:
                f.write(content)

            message_count += 1

        print(f"Exported {message_count} messages@#{channel.name} to {channel_dir}")
    except discord.Forbidden:
        print(f"Skipped #{channel.name}: missing read permission")

    return message_count


TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OUTPUT_DIR = Path(os.getenv("EXPORT_OUTPUT_DIR", "discord_exports"))
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} (id={bot.user.id})")
    print("Ready. Use command: !export_all !count_up !delete_all")


@bot.command(name="export_all")
@commands.has_permissions(administrator=True)
async def export_all(ctx: commands.Context) -> None:
    await ctx.send("Export started. This may take a while...")

    guild = ctx.guild
    if guild is None:
        await ctx.send("This command can only be used in a server channel.")
        return

    channel = ctx.channel
    guild_dir = f"{sanitize_filename(ctx.guild.name)}_{ctx.guild.id}"
    output_dir = OUTPUT_DIR / guild_dir
    try:
        message_count = await export_channel(channel, output_dir)
        await ctx.send(f"Export done. {message_count} posts exported to {output_dir}")
    except Exception as e:
        await ctx.send(f"Export failed: {e}")


@bot.command(name="count_up")
@commands.has_permissions(administrator=True)
async def count_up(ctx: commands.Context) -> None:
    await ctx.send("Start count...")
    print("count_up: start")
    msg_num = len([msg async for msg in ctx.channel.history(limit=None)])
    print("count_up: end")
    await ctx.send(f"This channel has {msg_num} messages")
    await ctx.send(f"Estimate time: {(msg_num * 20) / 60} min")

    return


@bot.command(name="delete_all")
@commands.has_permissions(administrator=True)
async def delete_all(ctx: commands.Context) -> None:
    await ctx.send("Delete all message start")
    print("delete_all: start")
    async for msg in ctx.channel.history(limit=None):
        await msg.delete()
    print("delete_all: end")
    await ctx.send("Deleted")

    return


@bot.command(name="delete_cmd")
@commands.has_permissions(administrator=True)
async def delete_cmd(ctx: commands.Context) -> None:
    await ctx.send("Delete command message start")
    print("delete_cmd: start")
    async for msg in ctx.channel.history(limit=None):
        if any([cmd in msg.content for cmd in CMD_SET]) or msg.author.bot:
            await msg.delete()
    print("delete_cmd: end")
    await ctx.send("delete end")

    return


def run_by_env() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")
    asyncio.run(bot.start(TOKEN))


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_by_env()

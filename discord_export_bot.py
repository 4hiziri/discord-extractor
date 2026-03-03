from playwright.async_api import async_playwright
import asyncio
import time
import random
import datetime as dt
import os
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urlextract import URLExtract
import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from markdownify import markdownify
import yt_dlp

import xcom_extractor

load_dotenv()

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


def format_message(msg: discord.Message) -> str:
    # timestamp = message.created_at.astimezone(dt.timezone.utc).isoformat()
    # author = f"{message.author} ({message.author.id})"
    content = msg.content

    attachment_lines = [f"attachment: {a.url}" for a in msg.attachments]

    embed_lines = []
    for embeds in msg.embeds:
        title = embeds.title
        description = embeds.description
        embed_lines.append(f"embed: title={title!r} description={description!r}")

    lines = [f"# {message_filename(msg)}\n", "## content\n"]
    lines += [content]
    if attachment_lines:
        lines.append("")
        lines.append("## attachments\n")
        lines.extend(attachment_lines)

    if embed_lines:
        lines.append("")
        lines.append("## embeds\n")
        lines.extend(embed_lines)

    return "\n".join(lines).strip() + "\n"


def message_filename(message: discord.Message) -> str:
    ts = message.created_at.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ts}_{message.id}"


async def fetch_normal_url_as_md(url) -> str:
    print(f"normal url: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )

        page = await context.new_page()

        await page.goto(url)
        await page.wait_for_load_state()
        content = await page.content()
        content = markdownify(content)

    return content

    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "discord-export-bot/1.0"},
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return f"not html content: <{url}>"

    soup = BeautifulSoup(response.text, "lxml")

    # for tag in soup(["script", "style", "noscript"]):
    #     tag.decompose()

    markdown = markdownify(str(soup), heading_style="ATX", default_title=True)
    media_urls = collect_media_urls(soup, url)

    return markdown.strip(), media_urls


async def fetch_xcom_as_md(url: str, media_path: Path) -> str:
    print(f"X: {url}")
    content = await xcom_extractor.xcom_extract(url, media_path)
    return markdownify(content, heading_style="ATX", default_title=True)


def fetch_youtube_as_md(url: str, media_path: Path) -> str:
    print(f"youtube: {url}")
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

    return f"### {url}\n\n![[{output}]]"


async def fetch_url_as_md(url: str, media_path: Path) -> str:
    match urlparse(url).netloc:
        case "x.com":
            md = await fetch_xcom_as_md(url, media_path)
        case "youtube.com":
            md = await fetch_youtube_as_md(url, media_path)
        case _:
            md = await fetch_normal_url_as_md(url)

    return md


def collect_media_urls(soup: BeautifulSoup, base_url: str) -> list[str]:
    media_urls: set[str] = set()

    for img in soup.select("img[src]"):
        media_urls.add(urljoin(base_url, img.get("src", "")))

    for video in soup.select("video[src]"):
        media_urls.add(urljoin(base_url, video.get("src", "")))

    for source in soup.select("video source[src], source[src]"):
        media_urls.add(urljoin(base_url, source.get("src", "")))

    return [u for u in sorted(media_urls) if is_media_url(u)]


def is_media_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in MEDIA_EXTENSIONS)


async def enrich_link_only_post(content: str, media_path: Path) -> str:
    """
    contentにURLが含まれている場合、それをmarkdownに展開して読み込む
    markdownに変換するのはfetch_url_as_mdで
    """

    print(f"DEBUG content: {content}")
    extractor = URLExtract()
    links = extractor.find_urls(content)
    links = list(set(links))

    if not links:
        return ""

    content = ""
    try:
        markdown_chunks: list[str] = []

        for link in links:
            markdown = await fetch_url_as_md(link, media_path)
            if markdown:
                markdown_chunks.append(markdown)
            time.sleep(random.randint(0, 3) + 5)

        if markdown_chunks:
            content += f"\n### {link}\n\n".join(markdown_chunks) + "\n"
    except Exception as e:
        print(f"Error at enrich_link_only_post: {e}")
        exit(1)

    return content


async def export_channel(channel: discord.Channel, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    message_count = 0

    try:
        channel_dir = output_dir / sanitize_filename(channel.name)
        channel_dir.mkdir(parents=True, exist_ok=True)

        async for msg in channel.history(limit=None, oldest_first=True):
            output_filename = channel_dir / (message_filename(msg) + ".md")
            media_path = channel_dir / (message_filename(msg) + "-media")
            media_path.mkdir(parents=True, exist_ok=True)

            content = format_message(msg)
            link_content = await enrich_link_only_post(content, media_path)
            if link_content != "":
                content += "\n## link contents\n\n"
                content += link_content

            with output_filename.open("w", encoding="utf-8") as f:
                f.write(content)

            message_count += 1

        print(
            f"Exported {message_count} messages from #{channel.name} -> {channel_dir}"
        )
    except discord.Forbidden:
        print(f"Skipped #{channel.name}: missing read permission")
    except Exception as e:
        print(f"Exception at export_channel: #{channel.name} - {e}")
        exit(1)

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
    print("Ready. Use command: !export_all")


@bot.command(name="export_all")
@commands.has_permissions(administrator=True)
async def export_all(ctx: commands.Context) -> None:
    await ctx.send("Export started. This may take a while...")

    guild = ctx.guild
    if guild is None:
        await ctx.send("This command can only be used in a server channel.")
        return

    channel = ctx.channel
    output_dir = OUTPUT_DIR / f"{sanitize_filename(ctx.guild.name)}_{ctx.guild.id}"
    message_count = await export_channel(channel, output_dir)
    await ctx.send(f"Export done. {message_count} posts exported to `{output_dir}`")


def run_by_env() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    asyncio.run(bot.start(TOKEN))


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_by_env()

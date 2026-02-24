import asyncio
import datetime as dt
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import discord
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from markdownify import markdownify as html_to_markdown

URL_ONLY_PATTERN = re.compile(r"https?://[\w.?=&#%~/-]+")
MEDIA_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".webm", ".mov", ".mkv"}
REQUEST_TIMEOUT = 20


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
    name = name.replace("\"", "_")
    return name


def format_message(message: discord.Message) -> str:
    timestamp = message.created_at.astimezone(dt.timezone.utc).isoformat()
    author = f"{message.author} ({message.author.id})"
    content = message.content or ""

    attachment_lines = [f"attachment: {a.url}" for a in message.attachments]

    embed_lines = []
    for e in message.embeds:
        title = e.title or ""
        description = e.description or ""
        embed_lines.append(f"embed: title={title!r} description={description!r}")

    lines = [content]
    if attachment_lines:
        lines.append("")
        lines.append("attachments:")
        lines.extend(attachment_lines)

    if embed_lines:
        lines.append("")
        lines.append("embeds:")
        lines.extend(embed_lines)

    return "\n".join(lines).strip() + "\n"


def message_filename(message: discord.Message) -> str:
    ts = message.created_at.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{ts}_{message.id}.txt"


def extract_link_if_content_only_link(content: str) -> str | None:
    match = URL_ONLY_PATTERN.match((content or "").strip())
    if not match:
        return None
    return match.group(1)


def fetch_url_as_markdown(url: str) -> tuple[str, str, list[str]]:
    response = requests.get(
        url,
        timeout=REQUEST_TIMEOUT,
        headers={"User-Agent": "discord-export-bot/1.0"},
    )
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return "", f"Skipped markdown conversion: non-HTML content ({content_type})", []

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    markdown = html_to_markdown(str(soup), heading_style="ATX")
    media_urls = collect_media_urls(soup, url)

    return markdown.strip(), media_urls


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


def download_media_files(media_urls: list[str], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []

    for index, url in enumerate(media_urls, start=1):
        parsed = urlparse(url)
        suffix = Path(parsed.path).suffix.lower() or ".bin"
        filename = f"{index:02d}_{sanitize_filename(Path(parsed.path).stem or 'media')}{suffix}"
        file_path = output_dir / filename

        try:
            with requests.get(
                url,
                stream=True,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": "discord-export-bot/1.0"},
            ) as response:
                response.raise_for_status()
                with file_path.open("wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            saved_files.append(str(file_path))
        except Exception as e:
            print(f"Failed media download: {url} ({e})")

    return saved_files


def enrich_link_only_post(message: discord.Message, message_text_path: Path) -> None:
    link = extract_link_if_content_only_link(message.content or "")
    if not link:
        return

    markdown_path = message_text_path.with_suffix(".md")
    media_dir = message_text_path.with_suffix("-media")

    try:
        markdown, media_urls = fetch_url_as_markdown(link)

        if markdown:
            markdown_path.write_text(markdown + "\n", encoding="utf-8")

        if media_urls:
            downloaded = download_media_files(media_urls, media_dir)
            if downloaded:
                with message_text_path.open("a", encoding="utf-8") as f:
                    f.write("\nlinked_media_files:\n")
                    for path in downloaded:
                        f.write(f"- {path}\n")

    except Exception as e:
        with message_text_path.open("a", encoding="utf-8") as f:
            f.write(f"\nlink_fetch_error: {e}\n")


def export_channel(channel: discord.TextChannel, output_dir: Path) -> int:
    channel_dir = output_dir / sanitize_filename(channel.name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for msg in channel.history(limit=None, oldest_first=True):
        output_path = channel_dir / message_filename(msg)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(format_message(msg))

        enrich_link_only_post(msg, output_path)
        count += 1

    print(f"Exported {count} messages from #{channel.name} -> {channel_dir}")
    return count


def export_guild(guild: discord.Guild, base_output_dir: Path) -> tuple[int, int]:
    guild_dir = base_output_dir / f"{guild.id}_{sanitize_filename(guild.name)}"
    guild_dir.mkdir(parents=True, exist_ok=True)

    channel_count = 0
    message_count = 0

    for channel in guild.text_channels:
        try:
            exported_messages = export_channel(channel, guild_dir)
            channel_count += 1
            message_count += exported_messages
        except discord.Forbidden:
            print(f"Skipped #{channel.name}: missing read permission")
        except Exception as e:
            print(f"Failed #{channel.name}: {e}")

    return channel_count, message_count


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

    channel_count, message_count = await export_guild(guild, OUTPUT_DIR)
    await ctx.send(
        f"Export done. {channel_count} channels / {message_count} posts exported to `{OUTPUT_DIR}`"
    )


async def run_by_env() -> None:
    if not TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN is not set")

    await bot.start(TOKEN)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.run(run_by_env())


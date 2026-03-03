from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import os
import yt_dlp
import requests


IMG_SIZE_PAT = re.compile(r"&name=.*")
IMG_TAG_PAT = re.compile(r'<img .*?src=".+?".*?>')


class PostNotFoundError(Exception):
    pass


class PostAddultCantRedaError(Exception):
    pass


class PostCantReadError(Exception):
    pass


def validation_post(text: str) -> None:
    not_found_text = "Hmm...this page doesn’t exist. Try searching for something else."
    adult_text = "Age-restricted adult content"
    need_login_text = "you’ll need to log in to X"
    if not_found_text in text:
        raise PostNotFoundError
    elif adult_text in text:
        raise PostAddultCantRedaError
    elif need_login_text in text:
        raise PostCantReadError


def is_valid_img(img: str) -> bool:
    if "https://pbs.twimg.com/profile_images" in img:
        return False
    if "emoji/v2/svg" in img:
        return False

    return True


async def xcom_extract(url: str, media_path: Path) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )

        page = await context.new_page()

        await page.goto(url)
        await page.wait_for_load_state()

        article = page.get_by_role("article")

        text = await article.text_content()

        try:
            validation_post(text)
        except PostNotFoundError:
            print(f"xcom_extract: {url} is not found. maybe deleted")
            return f"{url} is not found."

        except PostAddultCantRedaError:
            print(f"xcom_extract: {url} is adult only.")
            return f"{url} is adult only, need login."
        except PostCantReadError:
            print(f"xcom_extract: {url} needs login.")
            return f"{url} need login."

        html = await article.inner_html()
        bs = BeautifulSoup(html, "lxml")
        # extract content
        # img
        # アイコンはhttps://pbs.twimg.com/profile_images/*/*__normal.jpgになってるので除外する
        imgs = bs("img")
        imgs = [img["src"] for img in imgs]
        imgs = [img for img in imgs if is_valid_img(img)]

        for img in imgs:
            img = re.sub(IMG_SIZE_PAT, "", img)
            data = requests.get(img)
            data.raise_for_status()
            data = data.content

            pic_name = os.path.basename(img)
            file_name = pic_name.replace("?format=", ".")
            with open(media_path / file_name, "wb") as f:
                f.write(data)

            html = re.sub(IMG_TAG_PAT, f"![[./{media_path}/{file_name}]]", html)
            text = html

        if bs("video"):
            ydl_opt = {
                "outtmpl": f"{media_path}/%(title).150B.%(ext)s",
                "ffmpeg_location": "/usr/bin/ffmpeg",
                "format": "bestvideo+bestaudio/best",
                "break_on_reject": True,
                "sleep_interval": 3,
                "max_sleep_interval": 5,
            }
            with yt_dlp.YoutubeDL(ydl_opt) as y:
                retcode = y.download([url])
                if retcode != 0:
                    raise Exception(f"Cannot download video: {url}")
                output = y.prepare_filename(y.extract_info(url, download=True))
                html += f"\n![[{output}]]"

        await browser.close()

    return text

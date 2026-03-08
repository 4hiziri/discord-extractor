from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import os
import yt_dlp
import requests
from dotenv import load_dotenv
import time
import random


load_dotenv()


IMG_SIZE_PAT = re.compile(r"&name=.*")
IMG_TAG_PAT = re.compile(r'<img .*?src=".+?".*?>')


class PostNotFoundError(Exception):
    pass


class PostAddultCantRedaError(Exception):
    pass


class PostCantReadError(Exception):
    pass


class JSNotRunning(Exception):
    pass


def validation_post(text: str) -> None:
    not_found_text1 = "Hmm...this page doesn’t exist. Try searching for something else."
    not_found_text2 = "表示する内容がありません"
    not_found_text3 = "Nothing to see here"
    adult_text = "Age-restricted adult content"
    need_login_text = "you’ll need to log in to X"
    js_missing = "JavaScript is not available."

    if js_missing in text:
        raise JSNotRunning
    elif not_found_text1 in text or not_found_text2 in text or not_found_text3 in text:
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
        browser = await p.firefox.launch(headless=True)
        time.sleep(5)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
        )

        page = await context.new_page()
        await page.goto(url, timeout=60000, wait_until="load")
        time.sleep(10)
        content = await page.content()
        bs = BeautifulSoup(content, "lxml")
        bs.noscript.clear()
        text = bs.get_text()

        try:
            validation_post(text)
        except JSNotRunning:
            print(f"xcom_extract: JS not running @ {url}, need check!")
            exit(1)
        except PostNotFoundError:
            print(f"xcom_extract: {url} is not found, maybe deleted")
            return f"{url} is not found."
        except PostAddultCantRedaError:
            print(f"xcom_extract: {url} is adult only.")
            return f"{url} is adult only, need login."
        except PostCantReadError:
            print(f"xcom_extract: {url} needs login.")
            return f"{url} need login."

        article = bs.find("article")

        if article is None:
            raise Exception(f"xcom_extract: article missing, {bs.get_text()}")

        # extract content
        # img
        imgs = article.find_all("img")

        if imgs:
            media_path.mkdir(parents=True, exist_ok=True)
            for img in imgs:
                img_src = img["src"]
                if not is_valid_img(img_src):
                    continue

                img_url = re.sub(IMG_SIZE_PAT, "", img_src)
                data = requests.get(img_url)
                data.raise_for_status()
                data = data.content

                pic_name = os.path.basename(img_url)
                file_name = pic_name.replace("?format=", ".")
                with open(media_path / file_name, "wb") as f:
                    f.write(data)

                img.replace_with(BeautifulSoup(f'<img src="{media_path / file_name}">', "lxml"))
                time.sleep(3 + random.randint(0, 2))

                # html = re.sub(IMG_TAG_PAT, f"![[./{media_path}/{file_name}]]", html)
                # print(img)
                # html = html.replace(img, f'<img src="{media_path / file_name}">')

        # extract video
        if bs.find("video"):
            media_path.mkdir(parents=True, exist_ok=True)
            ydl_opt = {
                "outtmpl": f"{media_path}/%(title).150B.%(ext)s",
                "ffmpeg_location": "/usr/bin/ffmpeg",
                "format": "bestvideo+bestaudio/best",
                "break_on_reject": True,
                "sleep_interval": 5,
                "max_sleep_interval": 10,
            }
            with yt_dlp.YoutubeDL(ydl_opt) as y:
                retcode = y.download([url])
                if retcode != 0:
                    raise Exception(f"Cannot download video: {url}")
                # output = y.prepare_filename(y.extract_info(url, download=True))
        text = str(article)

        await browser.close()

    return text

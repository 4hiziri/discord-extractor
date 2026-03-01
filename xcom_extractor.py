from pathlib import Path
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
import yt_dlp


ydl_opt = {
    "outtmpl": "%(title).150B.%(ext)s",
    "ffmpeg_location": "/usr/bin/ffmpeg",
    "format": "bestvideo+bestaudio/best",
    "break_on_reject": True,
    "sleep_interval": 3,
    "max_sleep_interval": 5,
}


IMG_SIZE_PAT = re.compile(r"&name=.*")
FORMAT_PAT = re.compile(r"format=.+?&")


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
            text = f"{url} is not found."
        except PostAddultCantRedaError:
            print(f"xcom_extract: {url} is adult only.")
            text = f"{url} is adult only, need login."
        except PostCantReadError:
            print(f"xcom_extract: {url} needs login.")
            text = f"{url} need login."

        html = await article.inner_html()
        bs = BeautifulSoup(html, "lxml")
        # extract content
        ## img
        ## アイコンはhttps://pbs.twimg.com/profile_images/*/*__normal.jpgになってるので除外する
        imgs = bs("img")
        imgs = [img["src"] for img in imgs]
        imgs = [img for img in imgs if is_valid_img(img)]
        [
            "https://pbs.twimg.com/media/GY-F2UCaAAAoBq8?format=jpg&name=small",
            "https://pbs.twimg.com/media/GY-F2UEbkAAopmb?format=jpg&name=360x360",
            "https://pbs.twimg.com/media/GY-F2UIbAAIDdS8?format=jpg&name=360x360",
        ]

        for img in imgs:
            img = re.sub(IMG_SIZE_PAT, "", img)
            format = re.search  # :TODO extarct format
        if bs("video"):
            with yt_dlp.YoutubeDL(ydl_opt) as y:
                y.download([url])

        await browser.close()

    return text

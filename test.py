from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import lxml


def handle_response(response):
    # Xの内部API（TweetDetailなど）の通信を探す
    if response.status == 200:
        try:
            pass
            # data = response.json()
            # ここでJSONを解析して、本文や画像URLを抽出する
            # content = data["data"]
            # print(f"content: {content}")
        except Exception:
            pass


with sync_playwright() as p:
    # 規制を避けるため、User-Agentなどを偽装（iPhone等に見せかけると構造がシンプルになることも）
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0"
    )

    page = context.new_page()

    # レスポンスが返ってくるたびにhandle_responseを実行
    page.on("response", handle_response)

    page.goto("https://x.com/priyanshup1405/status/2026700317849694400")
    page.wait_for_timeout(5000)  # ロード待ち
    page.wait_for_load_state("domcontentloaded")
    article = page.locator("article")
    print(article.text_content())
    print("----------------------------------------------------------")
    print(dir(article))
    html = article.inner_html()
    bs = BeautifulSoup(html, "lxml")
    print(bs)
    page.screenshot(path="debug.png", full_page=True)
    browser.close()

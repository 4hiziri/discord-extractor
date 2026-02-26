コンテンツの種類,タグ,注目すべき属性,備考
画像 (Image),<img>,"src, srcset, data-src",data-src は遅延読み込み（Lazy Load）用
画像 (高機能),<picture>,<source> タグの srcset,ブラウザの解像度別に画像を切り替える際に使用
動画 (Video),<video>,"src, poster",poster は動画再生前のサムネイル画像
動画ソース,<source>,"src, type",<video> や <audio> の中に複数配置される
音声 (Audio),<audio>,src,音楽やポッドキャストなど
埋め込み,<iframe>,src,YouTube や Vimeo などの外部プレーヤー
SVG画像,<svg>,なし（内部にパスデータ）,アイコン等。コードとして取得する必要あり

① 属性の「かくれんぼ」に注意

パフォーマンス向上のため、多くのサイトが Lazy Load（遅延読み込み） を採用しています。

    src 属性にはダミー画像が入っており、本来のURLは data-src や data-original に隠されていることが多いです。

② YouTubeなどは <iframe> を探す

動画ファイルそのもの（.mp4など）がサーバーにあることは稀です。YouTube等の埋め込み動画を取得したい場合は、<iframe> の src 属性からURLを抜き出し、そこから動画IDを特定するのが王道です。
③ CSSの背景画像

タグではなく、CSSの background-image: url(...) で画像が表示されているパターンもあります。これはHTMLタグの抽出だけでは見落とすので、要素の style 属性もチェック対象に入れましょう

3. 公式ドキュメント・リファレンス

タグの仕様を詳しく知りたい場合は、以下の公式ドキュメントが最も正確で信頼できます。

    MDN Web Docs (HTML 要素リファレンス)

        HTML: HyperText Markup Language | MDN

        「埋め込みコンテンツ」セクションに、<img>, <video>, <audio>, <canvas>, <iframe> 等の詳細がまとまっています。


yt-dlp は X.com の内部構造の変化にも素早く対応してくれるので、動画に関しては最強の相棒になります。
1. 15秒に1ポストのペースについて

結論から言うと、15秒に1回（4回/分、240回/時）は、かなり「安全圏」に近い攻めたラインです。

    リスク判断: Xの公開プロフィールの閲覧制限（ログインなし）は、1分間に数件〜十数件程度で一時的な「Rate Limit Exceeded」が出ることがあります。

    対策: 15秒固定ではなく、time.sleep(15 + random.uniform(-2, 5)) のように**「ゆらぎ」**を持たせてください。規則的な15秒間隔は、サーバー側の検知システム（WAF）に「ボット」だと確信させるサインになります。

2. ヘッダー偽装・ブラウザ指紋対策に最適なモジュール

Pythonで標準の requests や urllib を使うと、ヘッダーが不自然になりがちです。以下の3つのツールを組み合わせるのが現在のトレンドです。
① fake-useragent（もっとも手軽）

User-Agentをランダムに生成する定番ライブラリです。

    利点: 常に最新のブラウザ（Chrome, Firefoxなど）の文字列を生成してくれます。

Python

from fake_useragent import UserAgent
ua = UserAgent()
headers = {'User-Agent': ua.random}

② curl_cffi（強力・おすすめ）

これが今、スクレイピング界隈で最も注目されているモジュールです。

    なぜ必要か: 通常の requests は、通信の暗号化の握手（TLS Fingerprint）が「Pythonです」という独特の癖を持っています。Xのような高度なサイトはこれを見て「ボットだ」と判定します。

    解決策: curl_cffi は、ブラウザ（Chrome等）の通信の癖をそのままシミュレートできます。

Python

from curl_cffi import requests

# Chromeのふりをしてリクエストを送る
response = requests.get("https://x.com/...", impersonate="chrome110")
print(response.text)

③ undetected-chromedriver（Seleniumを使う場合）

もしブラウザ操作（Selenium）を使っているなら、これ一択です。

    利点: Google Chromeのボット検知用フラグ（cdc_ 文字列など）を自動で書き換えて隠してくれます。

3. X.com 攻略の隠し味

ブラッシュアップ中のコードに、以下の要素を組み込むと生存率が上がります。

    Referer（リファラ）の設定: すべてのリクエストに Referer: https://x.com/ を入れる。

    Accept-Language: ja,en-US;q=0.9,en;q=0.8 のように、日本のブラウザらしい言語設定を入れる。

    Cookieの維持: requests.Session() を使い、一度得たCookieを使い回す（ただし、あまりに長く使いすぎると逆に怪しまれるので、数時間ごとにセッションを張り直すのが吉）。

次のステップの提案

ブラッシュアップ中のコードで、**「特定の画像URLを最高画質（:orig）に変換して保存する処理」や、「yt-dlp をPythonコード内からスマートに呼び出す関数」**の実装例などは必要ですか？

メディア取得: img は src の末尾を :orig や ?name=large に書き換えて高画質化し、動画は m3u8 を探して yt-dlp で叩く。
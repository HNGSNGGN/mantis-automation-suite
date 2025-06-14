#!/usr/bin/env python3
import time, sys, os, requests, feedparser
from datetime import datetime
import pytz
from slack_sdk.webhook import WebhookClient
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import boto3
from dotenv import load_dotenv

# --- 環境変数の読み込み ---
load_dotenv()
MANTIS_HOST = os.getenv("MANTIS_HOST", "http://mantis.example.com")
MANTIS_ID = os.getenv("MANTIS_ID")
MANTIS_PW = os.getenv("MANTIS_PW")
MANTIS_API_KEY = os.getenv("MANTIS_API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID", "1")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# --- 定数と初期設定 ---
TIME_FMT = "%Y-%m-%d %H:%M"
KST = pytz.timezone("Asia/Seoul")
RSS_URL = f"{MANTIS_HOST}/issues_rss.php?username={MANTIS_ID}&key={MANTIS_API_KEY}&project_id={PROJECT_ID}"

# --- サービスクライアントの初期化 ---
translate = boto3.client("translate", region_name=AWS_REGION)
webhook = WebhookClient(SLACK_WEBHOOK_URL)

# --- グローバル変数 ---
session = None
last_pub_ts = 0
sent_cache = set()

# --- 関数定義 ---
def aws_translate(text, target_lang="ja"):
    if not text: return ""
    try:
        response = translate.translate_text(
            Text=text, SourceLanguageCode="ko", TargetLanguageCode=target_lang
        )
        return response["TranslatedText"]
    except Exception as e:
        print(f"⚠️ [翻訳エラー] {text} → {e}")
        return text

def get_session():
    global session
    if session: return session
    
    opts = Options()
    opts.add_argument("--headless"); opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=opts)
    try:
        driver.get(f"{MANTIS_HOST}/login_page.php")
        driver.find_element(By.ID, "username").send_keys(MANTIS_ID)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        time.sleep(1)
        driver.find_element(By.ID, "password").send_keys(MANTIS_PW)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        time.sleep(3)
        driver.get(f"{MANTIS_HOST}/set_project.php?project_id={PROJECT_ID}")
        time.sleep(1)
        
        s = requests.Session()
        for c in driver.get_cookies():
            s.cookies.set(c["name"], c["value"], domain=c["domain"])
        session = s
        return session
    finally:
        driver.quit()

def parse_issue(html: str):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.text.strip()
    last_mod = soup.find("td", class_="bug-last-modified").text.strip()
    tgt_th = soup.find("th", class_="bug-target-version category")
    target = tgt_th.find_next_sibling("td").text.strip() if tgt_th else "UNKNOWN"
    
    bugnotes = soup.select("tr.bugnote")
    if not bugnotes: return None
    
    last = bugnotes[-1]
    user = last.select_one("a[title]").text.strip()
    time_txt = " ".join(last.select_one("p.small.lighter").text.strip().split()[:2])
    body = last.select_one("td.bugnote-note").get_text("\n").strip()

    return dict(title=title, last_mod=last_mod, target=target,
                comment_user=user, comment_time=time_txt, comment_body=body)

def build_msg(issue_id, url, info):
    title_jp = aws_translate(info["title"])
    user_jp = aws_translate(info["comment_user"])
    body_jp = aws_translate(info["comment_body"])

    return (
        f"🔗 {url}\n"
        f"📝 {title_jp}\n"
        f"📝 {info['title']}\n"
        f"🎯 target : {info['target']} 🧑‍💻 [{info['comment_user']}] {user_jp}\n"
        f"🇯🇵\n```{body_jp}```\n"
        f"🇰🇷\n```{info['comment_body']}```"
    )

def send_slack(text):
    try:
        webhook.send(text=text)
        print(f"✅ [送信] Slack送信完了")
    except Exception as e:
        print(f"❌ [エラー] Slack送信失敗: {e}")

def process_latest():
    global last_pub_ts, sent_cache
    
    try:
        feed = feedparser.parse(requests.get(RSS_URL, timeout=10).text)
    except Exception as e:
        print(f"❌ [エラー] RSSリクエスト失敗: {e}")
        return

    if feed.bozo or not feed.entries:
        return

    entry = sorted(feed.entries, key=lambda e: e.published_parsed, reverse=True)[0]
    pub_ts = time.mktime(entry.published_parsed)

    if pub_ts <= last_pub_ts:
        return
    
    last_pub_ts = pub_ts
    url = entry.link
    iid = url.split("=")[-1]
    
    try:
        html = get_session().get(url, timeout=10).text
        info = parse_issue(html)
    except Exception as e:
        print(f"❌ [エラー] イシューのパース失敗 ({url}):", e)
        return

    if not info or not info.get("comment_time"):
        return

    cache_key = f"{iid}_{info['comment_time']}"
    if cache_key in sent_cache:
        return
        
    try:
        lm = datetime.strptime(info["last_mod"], TIME_FMT).replace(tzinfo=KST)
        ct = datetime.strptime(info["comment_time"], TIME_FMT).replace(tzinfo=KST)
    except (ValueError, TypeError):
        return

    if abs((lm - ct).total_seconds()) <= 120:
        send_slack(build_msg(iid, url, info))
        sent_cache.add(cache_key)

def main():
    while True:
        start = time.time()
        try:
            print(f"⏱️  [{datetime.now(KST).strftime(TIME_FMT)}] 定期チェック開始...")
            process_latest()
        except Exception as e:
            print(f"🚨 [例外] 定期処理失敗: {e}", file=sys.stderr)
        
        elapsed = time.time() - start
        time.sleep(max(0, 60 - elapsed))

if __name__ == "__main__":
    main()

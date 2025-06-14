#!/usr/bin/env python3
import os, time, requests, smtplib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

# --- 環境変数の読み込み ---
load_dotenv()
MANTIS_HOST = os.getenv("MANTIS_HOST", "http://mantis.example.com")
MANTIS_ID = os.getenv("MANTIS_ID")
MANTIS_PW = os.getenv("MANTIS_PW")
PROJECT_ID = os.getenv("PROJECT_ID", "1")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# --- スクリプト実行 ---
now = datetime.now().strftime('%Y-%m-%d %H:%M')

# --- Seleniumでログインとプロジェクト選択 ---
options = Options()
options.add_argument('--headless'); options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)
try:
    driver.get(f"{MANTIS_HOST}/login_page.php")
    driver.find_element(By.ID, "username").send_keys(MANTIS_ID)
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    time.sleep(2)
    driver.find_element(By.ID, "password").send_keys(MANTIS_PW)
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
    time.sleep(5)
    driver.get(f"{MANTIS_HOST}/set_project.php?project_id={PROJECT_ID}")
    time.sleep(2)

    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
finally:
    driver.quit()

# --- CSVダウンロードと一時保存 ---
csv_url = f"{MANTIS_HOST}/csv_export.php"
response = requests.get(csv_url, cookies=cookies)

if 'text/csv' not in response.headers.get('Content-Type', ''):
    print("❌ CSVダウンロード失敗: レスポンスがCSVではありません。")
    exit()

filename = f"mantis_project_{PROJECT_ID}_{now.replace(':', '-')}.csv"
filepath = f"/tmp/{filename}"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(response.text)
print("✅ CSV保存完了:", filepath)

# --- Gmail経由でCSVを添付ファイルとして送信 ---
msg = MIMEMultipart()
msg["From"] = SMTP_USER
msg["To"] = SMTP_USER
msg["Subject"] = f"MANTIS CSV {now}"

with open(filepath, "rb") as file:
    part = MIMEBase("application", "octet-stream")
    part.set_payload(file.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

try:
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    server.send_message(msg)
    server.quit()
    print("✅ メール送信成功! 📎")
except Exception as e:
    print("❌ メール送信失敗:", str(e))
finally:
    if os.path.exists(filepath):
        os.remove(filepath)

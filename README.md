# Mantis自動化システム

MantisBTの課題更新をSlackへリアルタイムで通知し、全データをGoogle Sheetsに同期して日本語検索を可能にする社内向け自動化プロジェクトです。
[demo.mp4](./demo.mp4)
<br>

## プロジェクトの構成

このリポジトリには、以下の主要なスクリプトが含まれています。

-   `mantis_comment_monitor.py`: Mantisの最新コメントをリアルタイムで検知し、内容を翻訳してSlackに通知します。
-   `mantis_csv_mailer.py`: Mantisの全課題データをCSVファイルとして抽出し、Gmailに添付ファイルとして送信します。
-   `gsheet_importer.js`: Gmailに届いたCSV添付ファイルをGoogle Sheetsへ自動で同期するGoogle Apps Scriptコードです。

<br>

## 利用技術

-   **言語**: Python, Google Apps Script (JavaScript)
-   **主要ライブラリ**: Selenium, BeautifulSoup4, requests, boto3, slack_sdk
-   **インフラ**: Oracle Cloud (VM), AWS (Amazon Translate)

<br>

## セットアップ

1.  **必要なパッケージのインストール**
    ```bash
    pip install -r requirements.txt
    ```

2.  **環境変数の設定**
    `.env.example` を参考に `.env` ファイルを作成し、必要なキー情報を入力してください。

3.  **実行**
    各スクリプトは、VM上の`screen`や`crontab`を利用して実行することを想定しています。
    -   コメント通知: `python3 mantis_comment_monitor.py`
    -   CSV同期: `python3 mantis_csv_mailer.py`

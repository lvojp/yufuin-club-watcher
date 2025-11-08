"""複数の予約プランを巡回し、空室を検知したら Pushover 通知を送るシンプルなウォッチャーです。"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
from dotenv import load_dotenv

# 予約ページで空室がない場合に表示される文言。HTML 内からこの文字列を探して判定します。
UNAVAILABLE_TEXT = (
    "申し訳ありませんが、設定された条件でご利用できるプランがないか、予約受付を停止中です。"
)

# 監視したいプランをここへ並べます。辞書をコピーし、表示名 (label) と URL を書き換えてください。
# label は通知文にそのまま載るので、日付や人数などが分かるようにしておくと便利です。
URLS_TO_WATCH: List[Dict[str, str]] = [
    {
        "label": "2025-11-23 由布院倶楽部 2名+小児1名 (夕食付)",
        "url": (
            "https://www.hpdsp.net/yufuinclub/hw/hwp3100/hww3101.do"
            "?screenId=HWW3101&reSearchFlg=1&yadNo=308342&adultNum=2&child3Num=1"
            "&roomCrack=200100&stayYear=2025&stayMonth=11&stayDay=23&stayCount=1"
            "&pageNum=1&roomCount=1&minPrice=0&maxPrice=999999&mealType=1"
        ),
    },
    {
        "label": "2025-11-29 由布院倶楽部 2名+小児1名 (夕食付)",
        "url": (
            "https://www.hpdsp.net/yufuinclub/hw/hwp3100/hww3101.do"
            "?screenId=HWW3101&reSearchFlg=1&yadNo=308342&adultNum=2&child3Num=1"
            "&roomCrack=200100&stayYear=2025&stayMonth=11&stayDay=29&stayCount=1"
            "&pageNum=1&roomCount=1&minPrice=0&maxPrice=999999&mealType=1"
        ),
    },
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
# 各 URL の最新ステータスを保存し、「空室なし→空室あり」に変わったときだけ通知します。
# 次回も通知を受け取りたい場合はファイルを削除するか、該当 URL の記録を消してください。
STATE_FILE = DATA_DIR / "last_status.json"
# 実行状況を残すログファイル
LOG_FILE = DATA_DIR / "log.txt"
# 認証情報を読み込む .env ファイル
ENV_FILE = PROJECT_ROOT / ".env"

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"
PUSHOVER_APPLICATION_TOKEN_ENV = "PUSHOVER_APPLICATION_TOKEN"
PUSHOVER_USER_KEY_ENV = "PUSHOVER_USER_KEY"
# Pushover の通知タイトル
PUSHOVER_TITLE = "由布院クラブの更新"
# 既定の優先度 (通常通知)
PUSHOVER_PRIORITY = 0

# パソコンのブラウザー相当の User-Agent を設定し、通常の HTML を返してもらいます。
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

load_dotenv(dotenv_path=ENV_FILE)


def load_previous_state() -> Dict[str, bool]:
    """前回実行時に保存したステータス (url -> bool) を読み込みます。"""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        # ファイルが壊れていて読めない場合は空の状態から再開します。
        return {}


def save_state(state: Dict[str, bool]) -> None:
    """最新のステータスを書き込み、同じ通知が連続しないようにします。"""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def log_activity(label: str, status: str, notify_sent: bool = False) -> None:
    """実行内容をログファイルに記録します。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp} - Label: {label}, Status: {status}, Notification: {'sent' if notify_sent else 'not sent'}\n"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fp:
        fp.write(log_entry)


def check_single_url(label: str, url: str, timeout: float = 30.0) -> Dict[str, object]:
    """1件分の予約ページを取得し、判定結果を辞書で返します。"""
    result: Dict[str, object] = {
        "label": label,
        "url": url,
        "available": False,
        "unavailable_marker_found": False,
        "status_code": None,
        "error": None,
    }

    try:
        with httpx.Client(timeout=timeout, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        # タイムアウトや DNS エラーなど、通信に失敗した場合はこちらに入ります。
        result["error"] = f"リクエストに失敗しました: {exc}"
        return result

    result["status_code"] = response.status_code
    text = response.text

    marker_found = UNAVAILABLE_TEXT in text
    result["unavailable_marker_found"] = marker_found
    result["available"] = not marker_found

    return result


def build_notification_message(result: Dict[str, object]) -> str:
    """空室が見つかったときに Pushover へ投稿する本文を作成します。"""
    return f"{result['label']}\n{result['url']}"


def send_pushover_notification(message: str) -> Tuple[bool, str]:
    """Pushover へ通知を送り、成否と詳細を返します。"""
    token = os.getenv(PUSHOVER_APPLICATION_TOKEN_ENV, "").strip()
    user_key = os.getenv(PUSHOVER_USER_KEY_ENV, "").strip()
    if not token or not user_key:
        return (
            False,
            "Pushover の認証情報 (PUSHOVER_APPLICATION_TOKEN, PUSHOVER_USER_KEY) が設定されていません",
        )

    payload = {
        "token": token,
        "user": user_key,
        "title": PUSHOVER_TITLE,
        "message": message,
        "priority": PUSHOVER_PRIORITY,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(PUSHOVER_API_URL, data=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return False, f"Pushover への通知に失敗しました: {exc}"

    return True, "Pushover への通知を送信しました"


def main() -> int:
    """`python -m yufuin_club_watcher` から呼び出されるエントリーポイントです。"""
    previous_state = load_previous_state()
    current_state = previous_state.copy()

    for entry in URLS_TO_WATCH:
        label = entry["label"]
        url = entry["url"]

        result = check_single_url(label, url)

        # cron のログを tail したときに状況が分かるよう、簡潔に出力します。
        status_code = result["status_code"]
        status = "available" if result["available"] else "unavailable"
        print(f"[{label}] status={status} status_code={status_code}")

        if result["error"]:
            print(f"  error: {result['error']}", file=sys.stderr)
            # 状態が不明なときは記録を更新せず、次の巡回で再試行します。
            continue

        current_state[url] = bool(result["available"])

        # 「空室なし→空室あり」に変化したタイミングのみ通知します。
        was_available = previous_state.get(url, False)
        # result["available"] = True # notify test
        just_opened = result["available"] and not was_available

        if just_opened:
            message = build_notification_message(result)
            success, detail = send_pushover_notification(message)
            print(f"  notification: {detail}")
            if not success:
                # cron のメールに分かりやすく表示させるためヒントを出します。
                print("  tip: .env の認証情報や通信環境を確認してください", file=sys.stderr)

        log_activity(label, status, just_opened)

    save_state(current_state)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

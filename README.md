## yufuin-club-watcher

由布院倶楽部の予約ページを定期的にチェックし、空室が見つかったタイミングで [ntfy.sh](https://ntfy.sh/) へ投稿するシンプルなスクリプトです。監視したい URL を Python のリストに並べるだけで複数日を同時に追跡できます。

### 必要環境

- Python 3.9 以上
- [uv](https://github.com/astral-sh/uv)
- ntfy.sh へ HTTPS POST できること（追加の認証は不要）

### セットアップ

```bash
uv sync --locked          # 初回に仮想環境と依存パッケージを準備
source .venv/bin/activate # 必要なら仮想環境をアクティブ化
```

以降はどちらの方法でも実行できます。

```bash
# 仮想環境を有効にしている場合
yufuin-club-watcher

# 直接呼び出す場合
uv run --locked python -m yufuin_club_watcher
```

### 監視対象の設定

`src/yufuin_club_watcher/__main__.py` 内の `URLS_TO_WATCH` リストに監視したいプランを追加します。同じ辞書をコピーし、`label`（通知に表示したい名前）と `url` を入れ替えるだけです。

```python
URLS_TO_WATCH = [
    {
        "label": "2025-11-23 由布院倶楽部 2名+小児1名",
        "url": "https://www.hpdsp.net/...",
    },
    # 追加したい分だけ続ける
]
```

スクリプトは `data/last_status.json` に直近の状態を記録し、前回「空室なし」だったプランが「空室あり」になったときにだけ通知します。

### ntfy.sh の設定

- 既定では `https://ntfy.sh/yufuin_club` に投稿し、タイトルは `Orbital`、タグは `hotel,watcher` です。
- パスワード付きトピックを使いたい場合は `NTFY_TOPIC_URL` やヘッダーの設定をコード内で変更してください。
- iOS で通知を受け取る場合は ntfy の PWA か他サービス（IFTTT, Pushover など）を併用してください。

curl から動作を確認したいときは次のように送れます。

   ```bash
   curl -H "Title: Orbital" -d "バックテスト完了" https://ntfy.sh/yufuin_club
   ```

### 定期実行（cron 例）

```
*/5 * * * * cd /path/to/yufuin-club-watcher && \
  uv run --locked python -m yufuin_club_watcher \
  >> /var/log/yufuin-club.log 2>&1
```

- 5 分ごとに巡回する設定例です。必要に応じて間隔を調整してください。
- cron の前に手動実行し、LINE 通知が届くか確認するのがおすすめです。

### 他の通知手段について

- **IFTTT Webhooks**: `requests.post("https://maker.ifttt.com/trigger/...")` のように差し替えれば、メールや iOS の通知にも転送できます。
- **LINE Notify**: `send_ntfy_notification()` を書き換えれば LINE にも戻せます。ヘッダーを `Authorization: Bearer ...` に変えるだけでOKです。

### トラブルシューティング

- サイトの文言が変わり、空室があるのに検知できない場合は `UNAVAILABLE_TEXT` の文字列を更新してください。
- 一時的な通信エラーは標準エラー出力に表示され、状態は更新されません。数分待って再実行してください。

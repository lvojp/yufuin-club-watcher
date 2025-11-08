## yufuin-club-watcher

由布院倶楽部の予約ページを定期的にチェックし、空室が見つかったタイミングで [Pushover](https://pushover.net/) 通知を送るシンプルなスクリプトです。監視したい URL を Python のリストに並べるだけで複数日を同時に追跡できます。

### 必要環境

- Python 3.11 以上
- [uv](https://github.com/astral-sh/uv)
- `api.pushover.net` へ HTTPS POST できること
- 依存パッケージ（`httpx`, `python-dotenv` など）は `uv sync` 実行時にまとめて導入されます

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

### Pushover の準備

1. Pushover でアカウントを作成し、ユーザーキー（User Key）を控えます。
2. 「Create an Application/API Token」からアプリケーショントークンを作成します。
3. プロジェクト直下の `.env` に次のように入力します（このリポジトリにはプレースホルダーが入った `.env` を同梱しています）。`python-dotenv` が自動で読み込むため、追加の設定は不要です。

   ```env
   PUSHOVER_APPLICATION_TOKEN=your_application_token
   PUSHOVER_USER_KEY=your_user_key
   ```

4. 送信元タイトルは `由布院クラブの更新`、優先度は通常通知 (0) に固定されています。必要なら `src/yufuin_club_watcher/__main__.py` の定数を調整してください。

curl でテストする場合は Pushover 公式ドキュメントの例を参考に、同じ `token` と `user` を用いて POST できます。

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

スクリプトは `data/last_status.json` に直近の状態を記録し、前回「空室なし」だったプランが「空室あり」になったときにだけ通知します。ログは `data/log.txt` に追記されます。

### 定期実行（cron 例）

```
*/5 * * * * cd /path/to/yufuin-club-watcher && \
  uv run --locked python -m yufuin_club_watcher \
  >> /var/log/yufuin-club.log 2>&1
```

- 5 分ごとに巡回する設定例です。必要に応じて間隔を調整してください。
- cron の前に手動実行し、Pushover 通知が届くか確認するのがおすすめです。

### トラブルシューティング

- サイトの文言が変わり、空室があるのに検知できない場合は `UNAVAILABLE_TEXT` の文字列を更新してください。
- 一時的な通信エラーや Pushover の認証エラーは標準エラー出力に表示されます。`.env` の設定と通信環境を確認してください。

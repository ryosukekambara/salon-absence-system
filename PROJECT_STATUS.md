# 📊 美容室欠勤管理システム 完全ドキュメント

**最終更新:** 2025年10月22日 20:00
**ステータス:** 🔴 Renderデプロイ設定エラー対応中

---

## 📁 プロジェクト構成

### GitHubリポジトリ構造
```
salon-absence-system/
├── 📄 auth_notification_system.py     # メインアプリ（約1450行）
├── 📄 requirements.txt                # 依存ライブラリ定義
├── 🐳 Dockerfile                      # Docker設定（NEW - 10/22追加）
├── 📄 render.yaml                     # Render設定（Docker用に更新）
├── 📄 .dockerignore                   # Dockerビルド最適化（NEW - 10/22追加）
├── 📁 .github/workflows/
│   └── keep-alive.yml                 # Renderスリープ防止（5分ごと）
├── 📄 .env                            # 環境変数（Gitには含まれない）
├── 📄 absence_log.json                # 欠勤申請履歴（7件）
├── 📄 messages.json                   # LINEメッセージテンプレート
├── 📄 customer_mapping.json           # 顧客マッピング（現在は未使用）
├── 📄 test_salonboard_access.py       # SALON BOARDアクセステスト（NEW - 10/22追加）
├── 📄 test_salonboard_access2.py      # 詳細ヘッダーテスト（NEW - 10/22追加）
├── 📁 backup_customers_*.json         # 自動バックアップファイル群
└── 📄 .gitignore
```

### 🆕 最近の変更（10/22）
- ✅ Dockerfile追加（Playwright公式イメージ使用）
- ✅ render.yaml更新（Python → Docker環境）
- ✅ .python-version更新（3.12.7 → 3.11.9）
- ✅ test_salonboard_access.py追加（調査完了）
- ❌ build.sh削除（Docker化により不要）

---

## 🎨 技術スタック

### バックエンド

| 技術 | バージョン | 用途 | ステータス |
|------|-----------|------|-----------|
| Python | 3.11.9 (変更済み) | メイン言語 | ✅ 確定 |
| Flask | 3.0.0 | Webフレームワーク | ✅ 稼働中 |
| requests | 2.31.0 | HTTP通信 | ✅ 稼働中 |
| beautifulsoup4 | 4.12.2 | HTMLパース | ✅ 稼働中 |
| line-bot-sdk | 3.5.0 | LINE API | ⚠️ 送信エラーあり |
| gunicorn | 21.2.0 | WSGIサーバー | ✅ 稼働中 |
| playwright | 1.40.0 | ブラウザ自動化 | 🔴 デプロイ失敗中 |
| supabase | 2.0.0 | DBクライアント | ✅ 稼働中 |

### requirements.txt（確定版）
```
Flask==3.0.0
requests==2.31.0
beautifulsoup4==4.12.2
supabase==2.0.0
line-bot-sdk==3.5.0
python-dotenv==1.0.0
gunicorn==21.2.0
Werkzeug==3.0.1
playwright==1.40.0
```

### Dockerfile（場所: `/Dockerfile`）
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=10000
CMD gunicorn --bind 0.0.0.0:$PORT auth_notification_system:app
```

**重要ポイント:**
- Playwright公式イメージを使用（ブラウザとシステム依存関係がプリインストール済み）
- `playwright install` コマンドは不要（既にイメージに含まれている）
- root権限不要でビルド可能

---

## 💾 データベース

### Supabase（PostgreSQL）

**プロジェクト情報:**
- プロジェクト名: `salon-absence`
- プロジェクトID: `lsrbeugmqqqklywmvjjs`
- リージョン: Northeast Asia (Tokyo)
- URL: `https://lsrbeugmqqqklywmvjjs.supabase.co`

### テーブル構造

#### 1. customers テーブル（✅ 稼働中）
```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  line_user_id TEXT UNIQUE NOT NULL,
  customer_number INTEGER,              -- SALON BOARD顧客番号
  name_kana TEXT,                       -- カナ氏名
  name_kanji TEXT,                      -- 漢字氏名
  line_display_name TEXT,               -- LINE表示名
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**現在のデータ:**
- 登録顧客数: **22人**
- 例: かん、もえ、まさみ、😃ゆみこ😃、鞍野 麻未

**格納ファイル:** auth_notification_system.py（行77-137）
- `load_mapping()`: Supabaseから読み込み
- `save_mapping()`: Supabaseに保存

#### 2. absences テーブル（未使用）
```sql
CREATE TABLE absences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_name TEXT NOT NULL,
  reason TEXT,
  details TEXT,
  alternative_date TEXT,
  submitted_at TIMESTAMPTZ DEFAULT NOW()
);
```

**現在の状態:** テーブルは存在するが、未使用
**代わりに使用:** `absence_log.json`（ローカルファイル）

#### 3. messages テーブル（未使用）
```sql
CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  staff_name TEXT,
  reason TEXT,
  details TEXT
);
```

**現在の状態:** テーブルは存在するが、未使用
**代わりに使用:** `messages.json`（ローカルファイル）

---

## 🌐 システムURL・認証情報

### 本番環境
- **管理画面URL:** https://salon-absence-system.onrender.com/login
- **Webhook URL:** https://salon-absence-system.onrender.com/webhook
- **現在の状態:** ✅ 稼働中（Playwright機能は未実装）

### テストアカウント

| 権限 | ユーザー名 | パスワード |
|------|-----------|-----------|
| 管理者 | admin | admin123 |
| スタッフ | kambara | kambara123 |
| スタッフ | saori | saori123 |

### 環境変数（Render設定済み）

**ファイル:** `.env`（ローカル）、Render Environment Variables（本番）

```bash
LINE_CHANNEL_ACCESS_TOKEN=WNmJn...（設定済み）
SUPABASE_URL=https://lsrbeugmqqqklywmvjjs.supabase.co
SUPABASE_KEY=eyJhbGci...（設定済み）
SALONBOARD_LOGIN_ID=CD18317
SALONBOARD_LOGIN_PASSWORD=Ne8T2Hhi!
TEST_MODE=true
```

---

## ✅ 完了している機能

### 1. 認証システム

**ファイル:** `auth_notification_system.py` 行52-75
**エンドポイント:**
- `GET/POST /login` - ログイン画面
- `GET /logout` - ログアウト

**フロー:**
```
ユーザーがログイン
   ↓
POST /login
   ↓
session['username'] = 'admin' または 'kambara'
session['role'] = 'admin' または 'staff'
   ↓
リダイレクト: /admin または /staff/absence
```

**セキュリティ:**
- Flaskセッション管理
- 権限分離（admin/staff）
- ログイン必須のデコレータ使用

---

### 2. データベース連携（Supabase）

#### A. 顧客データ読み込み

**ファイル:** `auth_notification_system.py` 行77-105

```python
def load_mapping():
    # Supabase REST API に GET リクエスト
    # /rest/v1/customers?select=*
    # 返り値: {顧客名: {user_id, registered_at}}
```

**処理フロー:**
```
load_mapping() 呼び出し
   ↓
GET https://lsrbeugmqqqklywmvjjs.supabase.co/rest/v1/customers?select=*
   ↓
ヘッダー: apikey, Authorization
   ↓
JSON レスポンス受信
   ↓
辞書形式に変換: {"かん": {"user_id": "U902...", ...}}
```

#### B. 顧客データ保存

**ファイル:** `auth_notification_system.py` 行107-137

```python
def save_mapping(customer_name, user_id):
    # 1. 既存チェック (GET)
    # 2. 新規登録 (POST)
    # 3. バックアップ自動実行
    # 返り値: True/False
```

**処理フロー:**
```
save_mapping("かん", "U902...")
   ↓
GET /customers?line_user_id=eq.U902...（重複チェック）
   ↓
存在しない場合
   ↓
POST /customers
Body: {"name": "かん", "line_user_id": "U902..."}
   ↓
ステータス 201: 成功
   ↓
backup_customers() 自動実行
   ↓
return True
```

---

### 3. バックアップシステム

**ファイル:** `auth_notification_system.py` 行139-168
**出力先:** `backup_customers_YYYYMMDD_HHMMSS.json`

```python
def backup_customers():
    # Supabaseからデータ取得
    # JSONファイルに保存

schedule.every(24).hours.do(backup_customers)
```

**実行タイミング:**
- 起動時: 1回実行
- 以降: 24時間ごと自動実行
- 手動: 新規顧客登録時

**最新バックアップ例:**
```json
{
  "かん": {
    "user_id": "U9022782f05526cf7632902acaed0cb08",
    "registered_at": "2025-10-17T05:51:55.480589+00:00"
  },
  "もえ": {
    "user_id": "U4297a65f1d41c724774d78040ffba039",
    "registered_at": "2025-10-17T07:04:29.927751+00:00"
  }
}
```

---

### 4. スリープ防止システム

**ファイル:** `.github/workflows/keep-alive.yml`

```yaml
name: Keep Render Alive
on:
  schedule:
    - cron: '*/5 * * * *'  # 5分ごと
  workflow_dispatch:

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Render Service
        run: curl -I https://salon-absence-system.onrender.com/login
```

**効果:**
- ✅ Renderのスリープ（15分間無通信）を防止
- ✅ 5分ごとに自動アクセス
- ✅ 顧客からのLINEメッセージを確実に処理

**稼働状況:**
- ✅ 手動実行: 成功
- ✅ 自動実行: 成功（5分間隔）

---

### 5. 管理者画面（4画面）

#### A. メッセージ管理画面（/admin）

**ファイル:** `auth_notification_system.py` 行645-752
**データソース:** `messages.json`

**機能:**
- 📊 システム統計表示
  - 登録顧客数
  - 今月の欠勤申請数
  - 総欠勤申請数
- LINEメッセージテンプレート編集
  - 代替募集メッセージ
  - 代替確定通知
  - 欠勤確認通知
- `/update` へPOST → `messages.json` 更新

#### B. 登録顧客一覧（/customers）

**ファイル:** `auth_notification_system.py` 行754-826
**データソース:** Supabase `customers` テーブル

**機能:**
- Supabaseから顧客データ取得（`load_mapping()`）
- テーブル形式表示（顧客名/LINE ID/登録日時）
- JST時刻に自動変換

#### C. 顧客データ取込（/admin/scrape）

**ファイル:** `auth_notification_system.py` 行1237-1335
**データソース:** ホットペッパービューティー（URL入力）

**機能:**
- ホットペッパーURLから顧客情報をスクレイピング
- BeautifulSoup4でHTML解析
- 新規顧客を自動的にSupabaseに登録
- 結果をリアルタイム表示

**🔴 現在の状態:** 未完成（Playwright実装が必要な可能性）

#### D. 欠勤申請履歴（/absences）

**ファイル:** `auth_notification_system.py` 行1004-1136
**データソース:** `absence_log.json`

**機能:**
- 月別アコーディオン表示
- `toggleMonth()` JavaScript関数で開閉
- 当月はデフォルトで開く
- CSV出力機能（`/export/absences`）

**現在のデータ:** 7件の欠勤申請

---

### 6. スタッフ画面（3画面）

#### A. 欠勤申請フォーム（/staff/absence）

**ファイル:** `auth_notification_system.py` 行320-415

**入力項目:**
- 欠勤理由（必須・ドロップダウン）:
  - 体調不良
  - 育児・介護の急用
  - 冠婚葬祭（忌引）
  - 交通遅延・災害
  - 家庭の事情
  - その他
- 状況説明（必須・textarea）
- 代替可能日時（任意・textarea）

#### B. 確認画面（/confirm_absence）

**ファイル:** `auth_notification_system.py` 行417-505

**機能:**
- 入力内容の確認表示
- hidden input で値保持
- 戻る/送信ボタン

#### C. 送信処理（/submit_absence）

**ファイル:** `auth_notification_system.py` 行507-541
**データ保存:** `absence_log.json`

**処理フロー:**
```
POST /submit_absence
   ↓
1. save_absence() → absence_log.json に追記
   ↓
2. load_messages() → テンプレート読み込み
   ↓
3. LINE送信処理:
   ├─ 申請者本人へ確認通知
   └─ 他スタッフ全員へ代替募集通知
   ↓
4. /absence/success へリダイレクト
```

**❌ 現在の問題:**
- LINE送信が400エラーで失敗
- ログ: `[警告] LINE API エラー: 400 - {"message":"Failed to send messages"}`

---

### 7. LINE連携機能

#### A. Webhook受信（/webhook）

**ファイル:** `auth_notification_system.py` 行1378-1414

**処理フロー:**
```
顧客がLINEメッセージ送信
   ↓
LINE Platform → POST /webhook
   ↓
line_webhook() 関数実行
   ↓
1. request.json からイベント取得
2. プロフィール取得（displayName）
3. load_mapping()で既存チェック
   ↓
新規の場合
   ↓
4. save_mapping()でSupabaseに保存
   ├─ 成功: ✅ログ出力
   └─ 失敗: ❌ログ出力
   ↓
5. backup_customers()自動実行
   ↓
6. /customers画面に即反映
```

**実績:**
- ✅ かん: 登録成功
- ✅ もえ: 登録成功
- ✅ 合計22人登録済み

#### B. LINE送信関数（send_line_message）

**ファイル:** `auth_notification_system.py` 行251-306

```python
def send_line_message(user_id, message, max_retries=3):
    # リトライ機能付き（最大3回）
    # 指数バックオフ: 1秒、2秒、4秒
    # タイムアウト: 10秒
```

**❌ 現在の問題:**
- 400エラーで送信失敗
- リトライも全て失敗
- 原因調査中

---

## 🔴 実装中の機能（未完成）

### SALON BOARDスクレイピング機能

**目的:** スタッフ欠勤時に、その日の予約客へ自動でLINE通知を送信

#### 実装計画フロー

```
【管理者操作】
1. 欠勤申請を確認
   ↓
2. 管理画面で「10/21の予約客に通知」ボタンクリック
   ↓
【システム自動処理】
3. Playwright起動
   ↓
4. SALON BOARDにログイン
   ├─ URL: https://salonboard.com/login/
   ├─ ID: CD18317
   └─ PW: Ne8T2Hhi!
   ↓
5. 10/21のスケジュール画面を開く
   URL: https://salonboard.com/KLP/schedule/salonSchedule/
   ↓
6. 各予約枠から情報取得:
   ├─ 顧客名
   ├─ 顧客番号（例: 441）
   └─ 予約時刻
   ↓
7. Supabaseで顧客番号照合
   SELECT * FROM customers WHERE customer_number = 441
   ↓
8. LINE User ID取得
   ↓
9. LINE一斉送信
   ├─ 顧客A: 「申し訳ございません...」
   ├─ 顧客B: 「申し訳ございません...」
   └─ 顧客C: 「申し訳ございません...」
   ↓
10. 結果表示
    ✅ 送信成功: 3件
    ⚠️ 手動対応: 1件（新規顧客）
```

#### 技術的な詳細

**A. Playwrightセットアップ**

**実装予定ファイル:** `auth_notification_system.py`（新規関数）

```python
from playwright.sync_api import sync_playwright

def scrape_salonboard(date):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        page = browser.new_page()

        # ログイン処理
        page.goto('https://salonboard.com/login/')
        page.fill('input[name="login_id"]', LOGIN_ID)
        page.fill('input[name="password"]', PASSWORD)
        page.click('button[type="submit"]')

        # スケジュール画面
        page.goto(f'https://salonboard.com/KLP/schedule/salonSchedule/?date={date}')

        # 予約情報を取得
        reservations = []
        elements = page.query_selector_all('.scheduleReserveName')

        for el in elements:
            customer_name = el.get_attribute('title')
            # 顧客番号を取得するロジック
            reservations.append({
                'name': customer_name,
                'number': customer_number
            })

        browser.close()
        return reservations
```

**B. 顧客番号照合**

**実装予定ファイル:** `auth_notification_system.py`（新規関数）

```python
def get_line_user_id(customer_number):
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/customers',
        params={'customer_number': f'eq.{customer_number}'},
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
    )
    data = response.json()
    if data:
        return data[0]['line_user_id']
    return None
```

#### 🔴 調査結果（test_salonboard_access.py）

**ファイル:** `test_salonboard_access.py`、`test_salonboard_access2.py`

**調査日:** 2025年10月22日

**結果:**
```
✅ SALON BOARDにアクセス
❌ ステータスコード: 403 Forbidden
❌ レスポンス: "Access denied"

結論:
- SALON BOARDはBot検知システムを使用
- requests + beautifulsoup4 では403エラー
- Playwright（実ブラウザ）が必須
```

**詳細:**
- 基本的なUser-Agent: 403 Forbidden
- 詳細なブラウザヘッダー: 403 Forbidden
- Playwrightでの実ブラウザが必要

---

## 🚀 デプロイ状況

### 最新コミット（mainブランチ）

| コミットID | 内容 | 日時 | ステータス |
|-----------|------|------|-----------|
| 729896c | Switch to Docker deployment | 2025-10-22 | ✅ GitHub反映済み |
| 2f0d51b | Merge PR #1 (Playwright build) | 2025-10-22 | ✅ マージ完了 |
| 06f4f61 | Add Playwright build config | 2025-10-22 | ✅ 完了 |
| 869135c | Add SALON BOARD access test | 2025-10-22 | ✅ 完了 |
| 53a2e28 | Python 3.11.9にダウングレード | 2025-10-22 | ✅ 完了 |

### Git履歴
```
✅ Python 3.12.7 → 3.11.9 変更
✅ Dockerfile作成
✅ render.yaml更新（Docker用）
✅ test_salonboard_access.py作成
✅ build.sh削除
✅ mainブランチにマージ完了
```

### Renderデプロイ状況

**現在の問題:**
```
🔴 Renderがrender.yamlを読んでいない
🔴 Python環境でビルドされている（Dockerではない）
🔴 手動設定（Build Command/Start Command）が優先されている

原因:
- Renderダッシュボードの手動設定が残っている
- env: docker が反映されていない
- playwright install --with-deps がroot権限エラーを起こす
```

**手動設定（問題の原因）:**
```
Build Command:
pip install -r requirements.txt && python -m playwright install --with-deps chromium

Start Command:
python -u auth_notification_system.py

→ これらの手動設定がrender.yamlを上書きしている
```

---

## ❌ 現在発生中の問題

### 🔴 最優先（ブロッカー）

#### 1. Renderデプロイ設定エラー

**問題:**
```
Renderがrender.yamlを読んでいない
→ 手動設定が優先されている
→ Docker環境に切り替わらない
→ playwright install --with-deps でroot権限エラー
```

**エラーログ:**
```
Installing dependencies...
Switching to root user to install dependencies...
Password: su: Authentication failure
Failed to install browsers
Error: Installation process exited with code: 1
==> Build failed 😞
```

**根本原因:**
- Renderダッシュボードの手動設定（Build Command/Start Command）
- render.yamlは存在するが無視されている
- Environment設定がPythonのまま

**必要な解決策:**
- 手動設定を削除または上書き
- Docker環境への切り替え
- render.yamlの適用

**影響:**
- SALON BOARDスクレイピング機能が実装できない
- 欠勤時の予約客への自動通知ができない

---

#### 2. LINE送信エラー（400）

**問題:**
```
[警告] LINE API エラー: 400
{"message":"Failed to send messages"}
```

**ファイル:** `auth_notification_system.py` 行251-306（send_line_message関数）

**確認済み:**
- ✅ トークンは正しい
- ✅ トークンは有効
- ✅ Render環境変数は正しい

**未確認:**
- ⚠️ LINE Developers Console の「Channel features」
- ⚠️ プッシュメッセージの利用可否
- ⚠️ スタッフのLINE User IDが正しいか

**影響:**
- 欠勤申請後のLINE通知が送信できない
- スタッフへの代替募集通知が届かない

---

## ✅ 完了した改善（10/22）

1. ✅ **Docker化**
   - Dockerfile作成（Playwright公式イメージ使用）
   - render.yaml更新（env: docker）
   - .dockerignore追加
   - build.sh削除

2. ✅ **Python バージョン変更**
   - 3.12.7 → 3.11.9
   - .python-version更新
   - aiohttp互換性問題の解決

3. ✅ **SALON BOARD調査**
   - test_salonboard_access.py作成
   - Bot検知システムの確認
   - Playwright必須であることを確認

4. ✅ **データベーススキーマ拡張**
   - customer_number列追加
   - name_kana列追加
   - name_kanji列追加
   - line_display_name列追加
   - updated_at列追加

5. ✅ **バックアップ機能**
   - 24時間ごと自動実行
   - 新規登録時も自動実行

6. ✅ **スリープ防止（GitHub Actions）**
   - 5分ごと自動アクセス
   - 稼働確認済み

---

## 📝 今後のタスク

### 🔴 最優先（現在進行中）

1. **Renderデプロイ設定の修正**
   - [ ] 手動設定（Build/Start Command）の削除または上書き
   - [ ] Docker環境への切り替え確認
   - [ ] ビルド成功確認
   - [ ] Playwright動作確認

2. **LINE送信エラー解決**
   - [ ] LINE Developers Console確認
   - [ ] プッシュメッセージ設定確認
   - [ ] スタッフのLINE User ID確認
   - [ ] テスト送信

### 🟡 高優先度

1. **SALON BOARDスクレイピング実装**
   - [ ] ログイン処理実装
   - [ ] スケジュール画面から予約情報取得
   - [ ] 顧客番号抽出ロジック
   - [ ] Supabase照合処理

2. **欠勤通知の承認フロー**
   - [ ] 管理画面に「予約客に通知」ボタン追加
   - [ ] `/approve_absence/<id>` エンドポイント実装
   - [ ] 予約客への一斉通知処理

3. **顧客データ初期投入**
   - [ ] SALON BOARD顧客一覧スクレイピング
   - [ ] 792件全件取得
   - [ ] Supabaseに一括保存
   - [ ] customer_number自動設定

4. **申請日時のJST変換**
   - [ ] absence_list関数修正
   - [ ] UTC → JST変換処理追加
   - [ ] タイムゾーン表示の統一

### 🟢 通常優先度

1. **スタッフ申請確認機能**
   - [ ] `/staff/my_absences` 画面作成
   - [ ] 自分の申請履歴表示

2. **欠勤履歴のSupabase移行**
   - [ ] absence_log.json → absencesテーブル
   - [ ] save_absence() 書き換え
   - [ ] load_absences() 書き換え

3. **メッセージテンプレートのSupabase移行**
   - [ ] messages.json → messagesテーブル
   - [ ] load_messages() 書き換え
   - [ ] save_messages() 書き換え

4. **ログ削除機能**
   - [ ] 欠勤申請履歴に削除ボタン追加
   - [ ] 管理者権限チェック

---

## 📊 現在の稼働状況

### システム全体

| 項目 | ステータス | 備考 |
|------|-----------|------|
| 本番URL | ✅ 稼働中 | https://salon-absence-system.onrender.com |
| GitHub自動デプロイ | ✅ 設定済み | mainブランチへのpushで自動デプロイ |
| Supabase | ✅ 稼働中 | 22人の顧客データ |
| スリープ防止 | ✅ 稼働中 | GitHub Actions（5分ごと） |
| LINE送信 | ❌ エラー | 400エラーで失敗中 |
| Playwright | 🔴 未稼働 | Renderデプロイ失敗中 |

### データ状況

| 項目 | 状態 | 格納場所 |
|------|------|----------|
| 登録顧客数 | 22人 | Supabase `customers` テーブル |
| 欠勤申請数 | 7件 | `absence_log.json` |
| バックアップ | 自動実行中 | `backup_customers_*.json` |
| 最新バックアップ | 2025-10-22 | 24時間ごと更新 |

---

## 📁 ファイル構成詳細

### メインファイル

| ファイル | 行数 | 主な機能 | ステータス |
|---------|------|---------|-----------|
| auth_notification_system.py | ~1450行 | メインアプリ | ✅ 稼働中 |
| requirements.txt | 9行 | 依存関係定義 | ✅ 確定 |
| Dockerfile | 20行 | Docker設定 | ✅ 作成済み |
| render.yaml | 19行 | Render設定 | ✅ 更新済み |

### データファイル

| ファイル | 形式 | 用途 | 更新タイミング |
|---------|------|------|--------------|
| absence_log.json | JSON | 欠勤申請履歴 | 申請時 |
| messages.json | JSON | LINEテンプレート | 管理者編集時 |
| customer_mapping.json | JSON | 顧客マッピング | 未使用 |
| backup_customers_*.json | JSON | バックアップ | 24時間ごと |

### テストファイル

| ファイル | 用途 | 結果 |
|---------|------|------|
| test_salonboard_access.py | SALON BOARDアクセステスト | 403エラー確認 |
| test_salonboard_access2.py | 詳細ヘッダーテスト | Bot検知確認 |

---

## 🔄 次のアクション

### 今すぐ実行すべきこと

1. **Renderの手動設定を修正**
   - Build Command/Start Commandの確認
   - Docker環境への切り替え
   - 再デプロイ

2. **Playwrightビルド成功確認**
   - Dockerビルドログ確認
   - ブラウザインストール確認
   - 動作テスト

3. **LINE送信エラーの調査**
   - LINE Developers Console確認
   - エラーログの詳細分析
   - テスト送信

### その後の作業

4. **SALON BOARDスクレイピング機能実装**
   - ログイン処理
   - 予約情報取得
   - 顧客番号照合

5. **顧客データ792件初期投入**
   - SALON BOARD顧客一覧取得
   - 一括登録処理

6. **完全自動化の実現**
   - 欠勤申請 → 予約客通知の全自動フロー
   - エラーハンドリングの強化

---

**最終更新:** 2025年10月22日 20:00
**次の確認:** Renderデプロイ設定修正後のビルド結果

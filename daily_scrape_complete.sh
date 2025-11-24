#!/bin/bash

#==================================================
# サロン予約リマインド - 完全自動スクレイピングスクリプト
# クッキー自動再取得対応版
#==================================================

set -euo pipefail

SCRIPT_DIR="/Users/kanbararyousuke/salon-absence-system"
VENV_PATH="$SCRIPT_DIR/venv/bin/activate"
ENV_FILE="$SCRIPT_DIR/.env"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/scrape_$(date +%Y%m%d).log"
LOCK_FILE="/tmp/salon_scrape.lock"

MAX_RETRIES=3
RETRY_INTERVAL=900
VPS_HOST="ubuntu@153.120.1.43"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_error_notification() {
    local error_msg="$1"
    local date_label="$2"
    
    log "エラー通知送信: $error_msg"
    
    cd "$SCRIPT_DIR"
    source "$VENV_PATH"
    
    python3 << PYEOF
import os
import requests
from dotenv import load_dotenv

load_dotenv("$ENV_FILE")

message = """⚠️ スクレイピングエラー

${date_label}の予約取得に失敗しました。
サロンボードをご確認ください。

エラー: ${error_msg}
時刻: $(date '+%Y/%m/%d %H:%M')"""

url = 'https://api.line.me/v2/bot/message/push'
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("LINE_CHANNEL_ACCESS_TOKEN")}'
}
data = {
    'to': os.getenv('TEST_LINE_USER_ID'),
    'messages': [{'type': 'text', 'text': message}]
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    if response.status_code == 200:
        print("✅ エラー通知送信成功")
    else:
        print(f"❌ エラー通知送信失敗: {response.status_code}")
except Exception as e:
    print(f"❌ エラー通知送信失敗: {e}")
PYEOF
}

#--------------------------------------------------
# クッキー自動再取得関数
#--------------------------------------------------
refresh_cookie() {
    log "🔄 クッキー自動再取得開始..."
    
    cd "$SCRIPT_DIR"
    source "$VENV_PATH"
    
    # Headlessモードでクッキー取得
    python3 << PYEOF
from playwright.sync_api import sync_playwright
import json
import os
from dotenv import load_dotenv

load_dotenv("$ENV_FILE")

SALON_ID = os.getenv('SALON_ID')
SALON_PASSWORD = os.getenv('SALON_PASSWORD')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    # ログインページへ
    page.goto('https://salonboard.com/login/', timeout=60000)
    page.wait_for_load_state('networkidle')
    
    # ログイン
    page.fill('input[name="login_id"]', SALON_ID)
    page.fill('input[name="password"]', SALON_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    
    # クッキー保存
    cookies = context.cookies()
    with open('cookies.json', 'w') as f:
        json.dump(cookies, f)
    
    browser.close()
    print("✅ クッキー再取得成功")
PYEOF
    
    if [ $? -eq 0 ]; then
        log "✅ クッキー再取得成功"
        return 0
    else
        log "❌ クッキー再取得失敗"
        return 1
    fi
}

if [ -f "$LOCK_FILE" ]; then
    if [ $(($(date +%s) - $(stat -f %m "$LOCK_FILE"))) -gt 3600 ]; then
        log "古いロックファイルを削除"
        rm -f "$LOCK_FILE"
    else
        log "❌ 既に実行中です。終了します。"
        exit 1
    fi
fi

touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "=========================================="
log "スクレイピング処理開始"
log "=========================================="

mkdir -p "$LOG_DIR"
cd "$SCRIPT_DIR"
source "$VENV_PATH"

THREE_DAYS=$(date -v+3d +%Y%m%d)
SEVEN_DAYS=$(date -v+7d +%Y%m%d)

log "対象日付: 3日後=$THREE_DAYS, 7日後=$SEVEN_DAYS"

scrape_and_upload() {
    local target_date=$1
    local days_label=$2
    local output_filename=$3
    local cookie_refreshed=0
    
    log "------------------------------------------"
    log "[$days_label] 処理開始: $target_date"
    log "------------------------------------------"
    
    for attempt in $(seq 1 $MAX_RETRIES); do
        log "[$days_label] 試行 $attempt/$MAX_RETRIES"
        
        cp scrape_with_phone_final.py temp_scrape_${days_label}.py
        sed -i '' "17s/datetime.now().strftime('%Y%m%d')/'$target_date'/" temp_scrape_${days_label}.py
        
        if python3 temp_scrape_${days_label}.py >> "$LOG_FILE" 2>&1; then
            LATEST_JSON=$(ls -t scrape_result_with_phone_*.json 2>/dev/null | head -1)
            
            if [ -z "$LATEST_JSON" ]; then
                log "[$days_label] エラー: JSONファイルが見つかりません"
                rm -f temp_scrape_${days_label}.py
                continue
            fi
            
            FILE_SIZE=$(stat -f%z "$LATEST_JSON")
            
            if [ "$FILE_SIZE" -gt 200 ]; then
                log "[$days_label] ✅ スクレイピング成功 (${FILE_SIZE}バイト)"
                
                TIMESTAMPED_FILE="${days_label}_$(date +%Y%m%d_%H%M%S).json"
                cp "$LATEST_JSON" "$TIMESTAMPED_FILE"
                
                log "[$days_label] VPSに転送中..."
                
                if scp -o ConnectTimeout=30 "$LATEST_JSON" "${VPS_HOST}:~/${output_filename}" >> "$LOG_FILE" 2>&1; then
                    log "[$days_label] ✅ 転送成功"
                    rm -f temp_scrape_${days_label}.py
                    return 0
                else
                    log "[$days_label] ❌ 転送失敗"
                fi
            else
                log "[$days_label] ❌ 空のデータ (${FILE_SIZE}バイト) - クッキー無効の可能性"
                
                # クッキー再取得（1回のみ）
                if [ $cookie_refreshed -eq 0 ]; then
                    if refresh_cookie; then
                        cookie_refreshed=1
                        log "[$days_label] クッキー再取得成功、即座に再試行"
                        rm -f temp_scrape_${days_label}.py
                        continue
                    fi
                fi
            fi
        else
            log "[$days_label] ❌ スクレイピング失敗"
        fi
        
        rm -f temp_scrape_${days_label}.py
        
        if [ $attempt -lt $MAX_RETRIES ]; then
            log "[$days_label] $(($RETRY_INTERVAL / 60))分後にリトライ..."
            sleep $RETRY_INTERVAL
        fi
    done
    
    log "[$days_label] ❌ 全試行失敗"
    send_error_notification "3回のリトライすべて失敗" "$days_label ($target_date)"
    
    return 1
}

scrape_and_upload "$THREE_DAYS" "3日後" "scrape_result_3days.json"
THREE_DAYS_RESULT=$?

if [ $THREE_DAYS_RESULT -eq 0 ]; then
    log "Bot判定回避のため5分待機..."
    sleep 300
fi

scrape_and_upload "$SEVEN_DAYS" "7日後" "scrape_result_7days.json"
SEVEN_DAYS_RESULT=$?

log "=========================================="
if [ $THREE_DAYS_RESULT -eq 0 ] && [ $SEVEN_DAYS_RESULT -eq 0 ]; then
    log "✅ 全処理完了"
elif [ $THREE_DAYS_RESULT -eq 0 ] || [ $SEVEN_DAYS_RESULT -eq 0 ]; then
    log "⚠️ 部分的に完了"
else
    log "❌ 全処理失敗"
fi
log "=========================================="

exit 0

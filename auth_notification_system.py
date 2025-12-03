from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify, make_response
import requests
import os
import json
from datetime import datetime, timezone, timedelta
from functools import wraps
from dotenv import load_dotenv
from collections import defaultdict
import time
import csv
from io import StringIO
from bs4 import BeautifulSoup
import schedule
import threading
# from supabase import create_client の行は削除

load_dotenv()

def clean_customer_name(text):
    """名前を正規化（スペース除去、★除去、余計な文字除去）"""
    import re
    # 改行以降を除去（予約IDなど）
    name = text.split("\n")[0].strip()
    # 除去パターン
    remove_patterns = [
        r"★+",
        r"です[。\.]*$",
        r"でーす[。\.]*$",
        r"よろしく.*$",
        r"お願い.*$",
        r"初めまして.*$",
        r"はじめまして.*$",
        r"こんにちは.*$",
        r"こんばんは.*$",
        r"おはよう.*$",
        r"[。、\.!！\?？]+$",
    ]
    for pattern in remove_patterns:
        name = re.sub(pattern, "", name)
    # スペース除去（半角・全角両方）
    name = re.sub(r"[\s　]+", "", name)
    return name.strip()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Supabase接続を追加（ここから）
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
# supabase = create_client の行は削除
# Supabase接続を追加（ここまで）

LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_BOT_TOKEN_STAFF = os.getenv('LINE_CHANNEL_ACCESS_TOKEN_STAFF')
MAPPING_FILE = 'customer_mapping.json'
ABSENCE_FILE = 'absence_log.json'
MESSAGES_FILE = 'messages.json'

ADMIN_USERS = {
    'admin': 'admin123'
}

STAFF_USERS = {
    'kambara': {'password': 'kambara123', 'full_name': '神原', 'line_id': 'U3dafc1648cc64b066ca1c5b3f4a67f8e'},
    'saori': {'password': 'saori123', 'full_name': 'Saori', 'line_id': 'U1ad150fa84a287c095eb98186a8cdc45'}
}

staff_mapping = {
    "U3dafc1648cc64b066ca1c5b3f4a67f8e": {"name": "神原さん"},
    "U1ad150fa84a287c095eb98186a8cdc45": {"name": "Saoriさん"}
}

def load_messages():
    """メッセージをJSONファイルから読み込む（即時反映用）"""
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "absence_request": "{staff_name}が本日欠勤となりました。",
        "substitute_confirmed": "{substitute_name}が出勤してくれることになりました。",
        "absence_confirmed": "欠勤申請を受け付けました。"
    }

def save_messages(messages):
    """メッセージをJSONファイルに保存"""
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            return redirect(url_for('staff_absence'))
        return f(*args, **kwargs)
    return decorated_function

def load_mapping():
    try:
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/customers?select=*',
            headers=headers
        )
        
        if response.status_code == 200:
            result = {}
            for row in response.json():
                result[row['name']] = {
                    'user_id': row['line_user_id'],
                    'registered_at': row['registered_at']
                }
            return result
        return {}
    except Exception as e:
        print(f"Supabase読み込みエラー: {e}")
        return {}


def find_phone_from_bookings(name):
    """bookingsテーブルから電話番号を検索"""
    try:
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}'
        }
        response = requests.get(f'{SUPABASE_URL}/rest/v1/bookings?select=*', headers=headers)
        if response.status_code == 200:
            for booking in response.json():
                booking_name = booking.get('customer_name', '')
                if name in booking_name or booking_name in name:
                    phone = booking.get('phone')
                    customer_number = booking.get('customer_number')
                    if phone:
                        return phone, customer_number
        return None, None
    except Exception as e:
        print(f"電話番号検索エラー: {e}")
        return None, None

def save_mapping(customer_name, user_id):
    customer_name = clean_customer_name(customer_name)
    try:
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json'
        }
        
        # 既存チェック
        check_response = requests.get(
            f'{SUPABASE_URL}/rest/v1/customers?line_user_id=eq.{user_id}',
            headers=headers
        )
        
        if check_response.status_code == 200:
            existing_data = check_response.json()
            if len(existing_data) == 0:
                # 電話番号を検索
                phone, customer_number = find_phone_from_bookings(customer_name)
                # 新規登録
                data = {
                    'name': customer_name,
                    'line_user_id': user_id,
                    'registered_at': datetime.now().isoformat(),
                    'phone': phone,
                    'customer_number': customer_number
                }
                insert_response = requests.post(
                    f'{SUPABASE_URL}/rest/v1/customers',
                    headers=headers,
                    json=data
                )
                if insert_response.status_code == 201:
                    print(f"✓ {customer_name} をSupabaseに登録")
                    backup_customers()
                    return True
            else:
                # 既存ユーザーの名前を更新（フルネームで上書き）
                current_name = existing_data[0].get("name", "")
                if current_name != customer_name and len(customer_name) >= 2:
                    update_response = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/customers?line_user_id=eq.{user_id}",
                        headers=headers,
                        json={"name": customer_name}
                    )
                    if update_response.status_code in [200, 204]:
                        print(f"✓ {current_name} → {customer_name} に更新")
                        return True
    except Exception as e:
        print(f"Supabase保存エラー: {e}")
    return False

def load_absences():
    if os.path.exists(ABSENCE_FILE):
        with open(ABSENCE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def backup_customers():
    """顧客データをバックアップ"""
    try:
        mapping = load_mapping()
        backup_file = f'backup_customers_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"✓ バックアップ作成: {backup_file}")
    except Exception as e:
        print(f"バックアップエラー: {e}")

def run_scheduler():
    """バックアップスケジューラーを実行"""
    while True:
        schedule.run_pending()
        time.sleep(3600)

def save_absence(staff_name, reason, details, alternative_date):
    absences = load_absences()
    
    absences.append({
        "staff_name": staff_name,
        "reason": reason,
        "details": details,
        "alternative_date": alternative_date,
        "submitted_at": datetime.now().isoformat()
    })
    
    with open(ABSENCE_FILE, 'w', encoding='utf-8') as f:
        json.dump(absences, f, ensure_ascii=False, indent=2)

def group_absences_by_month(absences):
    grouped = defaultdict(list)
    for absence in absences:
        month_key = absence['submitted_at'][:7]
        grouped[month_key].append(absence)
    return dict(sorted(grouped.items(), reverse=True))

def get_full_name(username):
    if username in STAFF_USERS:
        return STAFF_USERS[username]['full_name']
    return username

def send_line_message(user_id, message, token=None, max_retries=3):
    if token is None:
        token = LINE_BOT_TOKEN
    """LINE送信（リトライ＋エラーログ機能付き）"""
    # テストモード：実際に送信しない
    if os.getenv("TEST_MODE", "false").lower() == "true":
        print(f"[テストモード] {user_id[:8]}... → {message[:30]}...")
        return True
    
    if not token:
        print("[エラー] LINE_BOT_TOKENが設定されていません")
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': message}]
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'https://api.line.me/v2/bot/message/push',
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                if attempt > 0:
                    print(f"[成功] {attempt + 1}回目の試行で送信成功")
                return True
            else:
                print(f"[警告] LINE API エラー: {response.status_code} - {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数バックオフ: 1秒、2秒、4秒
                    
        except requests.exceptions.Timeout:
            print(f"[エラー] タイムアウト (試行 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                
        except requests.exceptions.RequestException as e:
            print(f"[エラー] リクエスト失敗 (試行 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                
        except Exception as e:
            print(f"[エラー] 予期しないエラー: {str(e)}")
            return False
    
    print(f"[失敗] {max_retries}回の試行後も送信失敗")
    return False

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET'])
def login_page():
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>スタッフ管理システム</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #f5f5f5;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #6b5b47 0%, #8b7355 100%);
                color: white;
                padding: 40px 20px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }
            .login-box {
                background: white;
                border-radius: 0 0 10px 10px;
                padding: 30px;
            }
            .tabs {
                display: flex;
                border-bottom: 2px solid #e0e0e0;
                margin-bottom: 30px;
            }
            .tab {
                flex: 1;
                padding: 15px;
                text-align: center;
                border-bottom: 3px solid transparent;
            }
            .tab.active {
                border-bottom-color: #6b5b47;
                font-weight: bold;
                color: #333;
            }
            .tab.disabled {
                color: #ccc;
                cursor: not-allowed;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
            }
            input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 16px;
                box-sizing: border-box;
            }
            .login-btn {
                width: 100%;
                padding: 15px;
                background: #6b5b47;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
            }
            .login-btn:hover {
                background: #8b7355;
            }
            .error {
                color: #d32f2f;
                margin-bottom: 15px;
                padding: 10px;
                background: #ffebee;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>STAFF CONNECT</h1>
                <p>スムーズなシフト調整を</p>
            </div>
            <div class="login-box">
                <div class="tabs">
                    <div class="tab active">ログイン</div>
                    <div class="tab disabled">新規登録</div>
                    <div class="tab disabled">一覧</div>
                    <div class="tab disabled">パスワード変更</div>
                </div>
                
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
                
                <form method="POST" action="{{ url_for('login_action') }}">
                    <div class="form-group">
                        <label>ID</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>パスワード</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit" class="login-btn">ログイン</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    error = request.args.get('error')
    return render_template_string(template, error=error)

@app.route('/login', methods=['POST'])
def login_action():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if username in ADMIN_USERS and ADMIN_USERS[username] == password:
        session['logged_in'] = True
        session['username'] = username
        session['role'] = 'admin'
        return redirect(url_for('admin'))
    
    if username in STAFF_USERS and STAFF_USERS[username]['password'] == password:
        session['logged_in'] = True
        session['username'] = username
        session['role'] = 'staff'
        return redirect(url_for('staff_absence'))
    
    return redirect(url_for('login_page', error='IDまたはパスワードが正しくありません'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/staff/absence')
@login_required
def staff_absence():
    if session.get('role') != 'staff':
        return redirect(url_for('admin'))
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>欠勤申請</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .content { background: white; padding: 30px; border-radius: 8px; }
            .form-group { margin-bottom: 25px; }
            label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
            select, textarea, input { 
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-family: inherit;
                font-size: 14px;
                box-sizing: border-box;
            }
            textarea {
                resize: vertical;
                min-height: 80px;
            }
            .submit-btn { 
                width: 100%;
                padding: 15px;
                background: #6b5b47;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
            }
            .submit-btn:hover {
                background: #8b7355;
            }
            .btn { 
                padding: 10px 20px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin-left: 10px;
            }
            .history-btn {
                background: #4caf50;
            }
            .history-btn:hover {
                background: #45a049;
            }
            .logout-btn { 
                background: #d32f2f;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
            .note {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>欠勤申請</h1>
                <div>
                    <a href="{{ url_for('staff_my_absences') }}" class="btn history-btn">自分の申請履歴</a>
                    <a href="{{ url_for('logout') }}" class="btn logout-btn">ログアウト</a>
                </div>
            </div>
            
            <div class="content">
                <form method="POST" action="{{ url_for('confirm_absence') }}">
                    <div class="form-group">
                        <label>欠勤理由 <span style="color: #d32f2f;">*</span></label>
                        <select name="reason" required>
                            <option value="">選択してください</option>
                            <option value="体調不良">体調不良</option>
                            <option value="育児・介護の急用">育児・介護の急用</option>
                            <option value="冠婚葬祭（忌引）">冠婚葬祭（忌引）</option>
                            <option value="交通遅延・災害">交通遅延・災害</option>
                            <option value="家庭の事情">家庭の事情</option>
                            <option value="その他">その他</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label>状況説明 <span style="color: #d32f2f;">*</span></label>
                        <textarea name="details" required placeholder="簡潔に状況をお知らせください（1-2行程度）"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>代替可能日時（任意）</label>
                        <input type="text" name="alternative_date" placeholder="例: 明日以降であれば出勤可能">
                        <div class="note">代わりに出勤できる日があれば記入してください</div>
                    </div>
                    
                    <button type="submit" class="submit-btn">確認画面へ</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template)

@app.route('/confirm_absence', methods=['POST'])
@login_required
def confirm_absence():
    if session.get('role') != 'staff':
        return redirect(url_for('admin'))
    
    reason = request.form.get('reason')
    details = request.form.get('details')
    alternative_date = request.form.get('alternative_date', '')
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>送信確認</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .content { background: white; padding: 30px; border-radius: 8px; }
            h2 { color: #333; margin-bottom: 30px; text-align: center; }
            .confirm-item { margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 6px; }
            .confirm-label { font-weight: 600; color: #666; margin-bottom: 5px; }
            .confirm-value { color: #333; }
            .buttons { display: flex; gap: 15px; margin-top: 30px; }
            .btn { 
                flex: 1;
                padding: 15px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
                text-align: center;
                text-decoration: none;
                display: block;
            }
            .btn-submit {
                background: #6b5b47;
                color: white;
            }
            .btn-submit:hover {
                background: #8b7355;
            }
            .btn-back {
                background: #e0e0e0;
                color: #333;
            }
            .btn-back:hover {
                background: #d0d0d0;
            }
            .logout-btn { 
                background: #d32f2f;
                padding: 10px 20px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>送信確認</h1>
                <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
            </div>
            
            <div class="content">
                <h2>この内容で送信しますか？</h2>
                <p style="color: #ff9800; background: #fff3e0; padding: 12px; border-radius: 6px; margin: 20px 0; text-align: center;">
                    ⚠️ 送信すると全スタッフに通知が送られます ⚠️
                </p>
                
                <div class="confirm-item">
                    <div class="confirm-label">欠勤理由</div>
                    <div class="confirm-value">{{ reason }}</div>
                </div>
                
                <div class="confirm-item">
                    <div class="confirm-label">状況説明</div>
                    <div class="confirm-value">{{ details }}</div>
                </div>
                
                {% if alternative_date %}
                <div class="confirm-item">
                    <div class="confirm-label">代替可能日時</div>
                    <div class="confirm-value">{{ alternative_date }}</div>
                </div>
                {% endif %}
                
                <form method="POST" action="{{ url_for('submit_absence') }}">
                    <input type="hidden" name="reason" value="{{ reason }}">
                    <input type="hidden" name="details" value="{{ details }}">
                    <input type="hidden" name="alternative_date" value="{{ alternative_date }}">
                    
                    <div class="buttons">
                        <a href="{{ url_for('staff_absence') }}" class="btn btn-back">戻る</a>
                        <button type="submit" class="btn btn-submit">送信</button>
                    </div>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template, reason=reason, details=details, alternative_date=alternative_date)

@app.route('/submit_absence', methods=['POST'])
@login_required
def submit_absence():
    if session.get('role') != 'staff':
        return redirect(url_for('admin'))
    
    staff_name = session.get('username')
    reason = request.form.get('reason')
    details = request.form.get('details')
    alternative_date = request.form.get('alternative_date', '')
    
    save_absence(staff_name, reason, details, alternative_date)
    
    # メッセージを動的に読み込む
    MESSAGES = load_messages()
    
    full_name = get_full_name(staff_name)
    
    # 他のスタッフへの通知
    absence_message = MESSAGES["absence_request"].format(staff_name=full_name)
    for username, info in STAFF_USERS.items():
        if username != staff_name:
            send_line_message(info['line_id'], absence_message, LINE_BOT_TOKEN_STAFF)
    
    # 欠勤スタッフ本人への確認通知
    confirmation_message = MESSAGES["absence_confirmed"].format(
        reason=reason,
        details=details
    )
    send_line_message(STAFF_USERS[staff_name]['line_id'], confirmation_message, LINE_BOT_TOKEN_STAFF)
    
    return redirect(url_for('absence_success'))

@app.route('/absence/success')
@login_required
def absence_success():
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>送信完了</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; }
            .content { background: white; padding: 40px; border-radius: 8px; text-align: center; }
            .success-icon { font-size: 48px; color: #4caf50; margin-bottom: 20px; }
            h2 { color: #333; margin-bottom: 15px; }
            p { color: #666; margin-bottom: 30px; line-height: 1.6; }
            .buttons { display: flex; gap: 15px; justify-content: center; }
            .btn { 
                display: inline-block;
                padding: 12px 32px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            }
            .btn-primary {
                background: #6b5b47;
            }
            .btn-primary:hover {
                background: #8b7355;
            }
            .btn-secondary {
                background: #4caf50;  # 緑
            }
            .btn-secondary:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="content">
                <div class="success-icon">✓</div>
                <h2>欠勤申請を受け付けました</h2>
                <p>
                    他のスタッフおよびご自身のLINEに通知が送信されました。<br>
                    ご連絡ありがとうございます。
                </p>
                <div class="buttons">
                    <a href="{{ url_for('staff_my_absences') }}" class="btn btn-secondary">自分の申請履歴</a>
                    <a href="{{ url_for('logout') }}" class="btn btn-primary">ログアウト</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template)

@app.route('/staff/my_absences')
@login_required
def staff_my_absences():
    if session.get('role') != 'staff':
        return redirect(url_for('admin'))
    
    staff_name = session.get('username')
    absences = load_absences()
    
    # 自分の申請のみフィルタリング
    my_absences = [a for a in absences if a.get('staff_name') == staff_name]
    my_absences.reverse()  # 新しい順
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>自分の申請履歴</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #f5f5f5; margin: 0; }
            .container { max-width: 800px; margin: 0 auto; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .content { background: white; padding: 30px; border-radius: 8px; }
            .stats { background: #e3f2fd; padding: 20px; border-radius: 8px; margin-bottom: 30px; text-align: center; }
            .stats-number { font-size: 48px; font-weight: bold; color: #1976d2; }
            .stats-label { color: #666; margin-top: 10px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
            th { background: #f5f5f5; font-weight: bold; }
            .reason-badge { 
                background: #ffebee; 
                color: #d32f2f; 
                padding: 4px 8px; 
                border-radius: 4px; 
                font-size: 12px;
                font-weight: 500;
            }
            .btn { 
                padding: 12px 32px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            }
            .btn-back {
                background: #6b5b47;
            }
            .btn-back:hover {
                background: #8b7355;
            }
            .logout-btn { 
                background: #d32f2f;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
            .empty-message {
                text-align: center;
                color: #999;
                padding: 40px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>自分の申請履歴</h1>
                <div>
                    <a href="{{ url_for('staff_absence') }}" class="btn btn-back">新規申請</a>
                    <a href="{{ url_for('logout') }}" class="btn logout-btn">ログアウト</a>
                </div>
            </div>
            
            <div class="content">
                <div class="stats">
                    <div class="stats-number">{{ my_absences|length }}</div>
                    <div class="stats-label">合計申請回数</div>
                </div>
                
                {% if my_absences %}
                <table>
                    <tr>
                        <th>申請日時</th>
                        <th>欠勤理由</th>
                        <th>状況説明</th>
                        <th>代替可能日時</th>
                    </tr>
                    {% for absence in my_absences %}
                    <tr>
                        <td>{{ absence.submitted_at[:10] }} {{ absence.submitted_at[11:16] }}</td>
                        <td><span class="reason-badge">{{ absence.reason }}</span></td>
                        <td>{{ absence.details }}</td>
                        <td>{{ absence.alternative_date if absence.alternative_date else '-' }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% else %}
                <div class="empty-message">まだ申請はありません</div>
                {% endif %}
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template, my_absences=my_absences)

@app.route('/admin')
@admin_required
def admin():
    # メッセージを動的に読み込む
    MESSAGES = load_messages()
    
    # 統計情報を計算
    mapping = load_mapping()
    customer_count = len(mapping)
    
    absences = load_absences()
    total_absences = len(absences)
    
    # 今月の欠勤申請数
    current_month = datetime.now().strftime("%Y年%m月")
    monthly_absences = sum(1 for a in absences if a.get("submitted_at", "").startswith(datetime.now().strftime("%Y-%m")))
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>メッセージ管理</title>
        <style>
            body { font-family: Arial; padding: 20px 100px; background: #f5f5f5; margin: 0; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .nav-wrapper { margin-bottom: 20px; }
            .nav { background: white; padding: 15px 20px; border-radius: 8px; display: inline-flex; gap: 20px; }
            .nav-btn {
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
                font-size: 14px;
                white-space: nowrap;
            }
            .nav-btn.active {
                background: #6b5b47;
                color: white;
            }
            .nav-btn:not(.active) {
                background: #f5f5f5;
                color: #666;
            }
            .nav-btn:not(.active):hover {
                background: #e0e0e0;
            }
            .content { background: white; padding: 30px 40px; border-radius: 8px; }
            .form-group { margin-bottom: 25px; }
            label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
            textarea { 
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-family: inherit;
                font-size: 14px;
                line-height: 1.6;
                box-sizing: border-box;
            }
            .save-btn { 
                padding: 12px 32px;
                background: #6b5b47;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: bold;
            }
            .save-btn:hover {
                background: #8b7355;
            }
            .logout-btn { 
                background: #d32f2f;
                padding: 10px 20px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
            .success-message {
                background: #e8f5e9;
                color: #2e7d32;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>メッセージ管理画面</h1>
            <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
        </div>
        
        <div class="content" style="margin-bottom: 20px;">
            <h2 style="margin-top: 0; margin-bottom: 15px; font-size: 18px;">📊 システム統計</h2>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #1976d2;">{{ customer_count }}</div>
                    <div style="color: #666; margin-top: 5px;">登録顧客数</div>
                </div>
                <div style="background: #fff3e0; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #f57c00;">{{ monthly_absences }}</div>
                    <div style="color: #666; margin-top: 5px;">今月の欠勤申請</div>
                </div>
                <div style="background: #fce4ec; padding: 20px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 32px; font-weight: bold; color: #c2185b;">{{ total_absences }}</div>
                    <div style="color: #666; margin-top: 5px;">総欠勤申請数</div>
                </div>
            </div>
        </div>
        
        <div class="nav-wrapper">
            <div class="nav">
                <a href="{{ url_for('admin') }}" class="nav-btn active">メッセージ管理画面</a>
                <a href="{{ url_for('customer_list') }}" class="nav-btn">登録顧客一覧</a>
                <a href="{{ url_for('scrape_page') }}" class="nav-btn">顧客データ取込</a>
                <a href="{{ url_for('absence_list') }}" class="nav-btn">欠勤申請履歴</a>
            </div>
        </div>
        
        <div class="content">
            {% if success %}
            <div class="success-message">✓ メッセージを保存しました（即時反映済み）</div>
            {% endif %}
            
            <form method="POST" action="{{ url_for('update') }}">
                <div class="form-group">
                    <label>代替募集メッセージ（欠勤以外のスタッフへ）:</label>
                    <textarea name="absence_request" rows="5">{{ messages.absence_request }}</textarea>
                </div>
                <div class="form-group">
                    <label>代替確定通知（欠勤以外のスタッフへ）:</label>
                    <textarea name="substitute_confirmed" rows="3">{{ messages.substitute_confirmed }}</textarea>
                </div>
                <div class="form-group">
                    <label>欠勤確認通知（欠勤スタッフ本人へ）:</label>
                    <textarea name="absence_confirmed" rows="4">{{ messages.absence_confirmed }}</textarea>
                </div>
                <button type="submit" class="save-btn">保存</button>
            </form>
        </div>
    </body>
    </html>
    '''
    success = request.args.get('success')
    return render_template_string(template, messages=MESSAGES, success=success, 
                                 customer_count=customer_count, monthly_absences=monthly_absences, 
                                 total_absences=total_absences)

@app.route('/customers')
@admin_required
def customer_list():
    mapping = load_mapping()
    
    # JST変換処理を追加
    JST = timezone(timedelta(hours=9))
    for customer_name, customer_data in mapping.items():
        if isinstance(customer_data, dict) and 'registered_at' in customer_data:
            try:
                utc_time = datetime.fromisoformat(customer_data['registered_at'].replace('Z', '+00:00'))
                jst_time = utc_time.astimezone(JST)
                customer_data['registered_at'] = jst_time.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>顧客一覧</title>
        <style>
            body { font-family: Arial; padding: 20px 100px; background: #f5f5f5; margin: 0; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .nav-wrapper { margin-bottom: 20px; }
            .nav { background: white; padding: 15px 20px; border-radius: 8px; display: inline-flex; gap: 20px; }
            .nav-btn {
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
                font-size: 14px;
                white-space: nowrap;
            }
            .nav-btn.active {
                background: #6b5b47;
                color: white;
            }
            .nav-btn:not(.active) {
                background: #f5f5f5;
                color: #666;
            }
            .nav-btn:not(.active):hover {
                background: #e0e0e0;
            }
            .content { background: white; padding: 30px 40px; border-radius: 8px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
            th { background: #f5f5f5; font-weight: bold; }
            .logout-btn { 
                background: #d32f2f;
                padding: 10px 20px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>登録顧客一覧</h1>
            <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
        </div>
        
        <div class="nav-wrapper">
            <div class="nav">
                <a href="{{ url_for('admin') }}" class="nav-btn">メッセージ管理画面</a>
                <a href="{{ url_for('customer_list') }}" class="nav-btn active">登録顧客一覧</a>
                <a href="{{ url_for('scrape_page') }}" class="nav-btn">顧客データ取込</a>
                <a href="{{ url_for('absence_list') }}" class="nav-btn">欠勤申請履歴</a>
            </div>
        </div>
        
        <div class="content">
            <p><strong>合計: {{ mapping|length }}人</strong></p>
            <table>
                <tr>
                    <th>顧客名</th>
                    <th>LINE User ID</th>
                    <th>登録日時</th>
                </tr>
                {% for name, data in mapping.items() %}
                <tr>
                    <td>{{ name }}</td>
                    <td>{{ data.user_id if data.user_id else data }}</td>
                    <td>{{ data.registered_at if data.registered_at else '-' }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template, mapping=mapping)

@app.route('/absences')
@admin_required
def absence_list():
    absences = load_absences()
    grouped_absences = group_absences_by_month(absences)
    current_month = datetime.now().strftime('%Y-%m')
    
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>欠勤申請履歴</title>
        <style>
            body { font-family: Arial; padding: 20px 100px; background: #f5f5f5; margin: 0; }
            .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
            .nav-wrapper { margin-bottom: 20px; }
            .nav { background: white; padding: 15px 20px; border-radius: 8px; display: inline-flex; gap: 20px; }
            .nav-btn {
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
                transition: all 0.3s;
                border: none;
                cursor: pointer;
                font-size: 14px;
                white-space: nowrap;
            }
            .nav-btn.active {
                background: #6b5b47;
                color: white;
            }
            .nav-btn:not(.active) {
                background: #f5f5f5;
                color: #666;
            }
            .nav-btn:not(.active):hover {
                background: #e0e0e0;
            }
            .content { background: white; padding: 30px 40px; border-radius: 8px; }
            .month-section { margin-bottom: 30px; }
            .month-header {
                background: #f5f5f5;
                padding: 12px 20px;
                border-radius: 6px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: pointer;
                margin-bottom: 10px;
            }
            .month-header:hover {
                background: #e8e8e8;
            }
            .month-title { font-weight: 600; font-size: 16px; }
            .month-count { color: #666; font-size: 14px; }
            .month-content { display: none; }
            .month-content.active { display: block; }
            .toggle-icon { transition: transform 0.3s; }
            .toggle-icon.rotated { transform: rotate(180deg); }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }
            th { background: #f5f5f5; font-weight: bold; }
            .reason-badge { 
                background: #ffebee; 
                color: #d32f2f; 
                padding: 4px 8px; 
                border-radius: 4px; 
                font-size: 12px;
                font-weight: 500;
            }
            .logout-btn { 
                background: #d32f2f;
                padding: 10px 20px;
                color: white;
                text-decoration: none;
                border-radius: 6px;
            }
            .logout-btn:hover {
                background: #b71c1c;
            }
        </style>
    </head>
    <body>
        <div class="header">
    <h1>欠勤申請履歴</h1>
    <div style="display: flex; align-items: center; gap: 15px;">
        <a href="{{ url_for('export_absences') }}" style="background: #4caf50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold;">CSV出力</a>
        <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
    </div>
</div>
        
        <div class="nav-wrapper">
            <div class="nav">
                <a href="{{ url_for('admin') }}" class="nav-btn">メッセージ管理画面</a>
                <a href="{{ url_for('customer_list') }}" class="nav-btn">登録顧客一覧</a>
                <a href="{{ url_for('scrape_page') }}" class="nav-btn">顧客データ取込</a>
                <a href="{{ url_for('absence_list') }}" class="nav-btn active">欠勤申請履歴</a>
            </div>
        </div>
        
        <div class="content">
            <p><strong>合計: {{ absences|length }}件</strong></p>
            
            {% if grouped_absences %}
                {% for month, month_absences in grouped_absences.items() %}
                <div class="month-section">
                    <div class="month-header" onclick="toggleMonth('{{ month }}')">
                        <div>
                            <span class="month-title">{{ month[:4] }}年{{ month[5:7]|int }}月</span>
                            <span class="month-count">（{{ month_absences|length }}件）</span>
                        </div>
                        <span class="toggle-icon" id="icon-{{ month }}">▼</span>
                    </div>
                    <div class="month-content {% if month == current_month %}active{% endif %}" id="content-{{ month }}">
                        <table>
                            <tr>
                                <th>スタッフ名</th>
                                <th>欠勤理由</th>
                                <th>状況説明</th>
                                <th>代替可能日時</th>
                                <th>申請日時</th>
                            </tr>
                            {% for absence in month_absences|reverse %}
                            <tr>
                                <td>{{ get_full_name(absence.staff_name) }}</td>
                                <td><span class="reason-badge">{{ absence.reason }}</span></td>
                                <td>{{ absence.details }}</td>
                                <td>{{ absence.alternative_date if absence.alternative_date else '-' }}</td>
                                <td>{{ absence.submitted_at[:10] }} {{ absence.submitted_at[11:16] }}</td>
                            </tr>
                            {% endfor %}
                        </table>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: #999; text-align: center; padding: 40px 0;">欠勤申請はまだありません</p>
            {% endif %}
        </div>
        
        <script>
            function toggleMonth(month) {
                const content = document.getElementById('content-' + month);
                const icon = document.getElementById('icon-' + month);
                content.classList.toggle('active');
                icon.classList.toggle('rotated');
            }
            
            window.onload = function() {
                const currentMonth = '{{ current_month }}';
                const currentIcon = document.getElementById('icon-' + currentMonth);
                if (currentIcon) {
                    currentIcon.classList.add('rotated');
                }
            };
        </script>
    </body>
    </html>
    '''
    return render_template_string(template, absences=absences, grouped_absences=grouped_absences, 
                                   current_month=current_month, get_full_name=get_full_name)

@app.route('/update', methods=['POST'])
@admin_required
def update():
    absence_msg = request.form.get('absence_request')
    substitute_msg = request.form.get('substitute_confirmed')
    absence_conf_msg = request.form.get('absence_confirmed')
    
    # JSONファイルとして保存（改行もそのまま保存される）
    messages = {
        "absence_request": absence_msg,
        "substitute_confirmed": substitute_msg,
        "absence_confirmed": absence_conf_msg
    }
    save_messages(messages)
    
    return redirect(url_for('admin', success='1'))

@app.route('/webhook/line', methods=['POST'])
def webhook():
    try:
        # メッセージを動的に読み込む
        MESSAGES = load_messages()
        
        events = request.json.get('events', [])
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                text = event['message']['text']
                staff_info = staff_mapping.get(user_id)
                
                if staff_info:
                    staff_name = staff_info['name']
                    
                    if "欠勤" in text or "休み" in text:
                        for uid, info in staff_mapping.items():
                            if uid != user_id:
                                msg = MESSAGES["absence_request"].format(staff_name=staff_name)
                                send_line_message(uid, msg)
                    
                    elif "出勤" in text or "できます" in text:
                        for uid, info in staff_mapping.items():
                            if uid != user_id:
                                notification = MESSAGES["substitute_confirmed"].format(substitute_name=staff_name)
                                send_line_message(uid, notification)
                
                else:
                    mapping = load_mapping()
                    existing = None
                    for name, data in mapping.items():
                        stored_id = data['user_id'] if isinstance(data, dict) else data
                        if stored_id == user_id:
                            existing = name
                            break
                    
                    # 新規でも既存でも名前更新を試みる
                    if len(text) >= 2:
                        cleaned_name = clean_customer_name(text)
                        if cleaned_name and len(cleaned_name) >= 2:
                            result = save_mapping(cleaned_name, user_id)
                        
        return 'OK', 200
    except Exception as e:
        return 'Error', 500

@app.route("/api/scrape-hotpepper", methods=["POST"])
@admin_required
def scrape_hotpepper():
    """ホットペッパーから顧客情報をスクレイピング"""
    try:
        data = request.json
        url = data.get("url")
        
        if not url:
            return jsonify({"success": False, "error": "URLが必要です"}), 400
        
        # 実際のページを取得
        response = requests.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(response.text, 'html.parser')
        
        customers = []
        new_count = 0
        
        # ホットペッパーの予約情報を抽出
        for elem in soup.find_all(['span', 'div', 'td'], class_=['customer', 'name', 'reservation']):
            name = elem.get_text().strip()
            if name and len(name) >= 2 and len(name) <= 20:
                mapping = load_mapping()
                if name not in mapping:
                    temp_id = f"pending_{datetime.now().timestamp()}"
                    save_mapping(name, temp_id)
                    customers.append({"name": name, "status": "新規登録"})
                    new_count += 1
                else:
                    customers.append({"name": name, "status": "登録済み"})
        
        return jsonify({
            "success": True, 
            "customers": customers, 
            "count": len(customers),
            "new_count": new_count,
            "message": f"合計{len(customers)}件（新規{new_count}件）を取得しました"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/admin/scrape")
@admin_required
def scrape_page():
    """スクレイピング管理画面"""
    SCRAPE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>顧客データ取込</title>
    <style>
        body { font-family: Arial; padding: 20px 100px; background: #f5f5f5; margin: 0; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .nav-wrapper { margin-bottom: 20px; }
        .nav { background: white; padding: 15px 20px; border-radius: 8px; display: inline-flex; gap: 20px; }
        .nav-btn {
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            font-size: 14px;
            white-space: nowrap;
        }
        .nav-btn.active {
            background: #6b5b47;
            color: white;
        }
        .nav-btn:not(.active) {
            background: #f5f5f5;
            color: #666;
        }
        .nav-btn:not(.active):hover {
            background: #e0e0e0;
        }
        .content { background: white; padding: 30px 40px; border-radius: 8px; }
        .logout-btn { 
            background: #d32f2f;
            padding: 10px 20px;
            color: white;
            text-decoration: none;
            border-radius: 6px;
        }
        .logout-btn:hover {
            background: #b71c1c;
        }
        input { width: 100%; padding: 12px; margin: 15px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button { background: #6b5b47; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
        button:hover { background: #5a4a37; }
        #result { margin-top: 20px; padding: 15px; border-radius: 4px; }
        #result h3 { margin: 0 0 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>ホットペッパー顧客データ取込</h1>
        <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
    </div>
    
    <div class="nav-wrapper">
        <div class="nav">
            <a href="{{ url_for('admin') }}" class="nav-btn">メッセージ管理画面</a>
            <a href="{{ url_for('customer_list') }}" class="nav-btn">登録顧客一覧</a>
            <a href="{{ url_for('scrape_page') }}" class="nav-btn active">顧客データ取込</a>
            <a href="{{ url_for('absence_list') }}" class="nav-btn">欠勤申請履歴</a>
        </div>
    </div>
    
    <div class="content">
        <form onsubmit="scrapeData(event)">
            <label style="font-weight: bold; display: block; margin-bottom: 5px;">ホットペッパーURL:</label>
            <input type="url" id="url" placeholder="https://..." required>
            <button type="submit">データ取得</button>
        </form>
        <div id="result"></div>
    </div>
    
    <script>
    async function scrapeData(e) {
        e.preventDefault();
        const url = document.getElementById("url").value;
        const result = document.getElementById("result");
        result.innerHTML = "<p>取得中...</p>";
        result.style.background = "#e3f2fd";
        result.style.border = "1px solid #2196f3";
        try {
            const response = await fetch("/api/scrape-hotpepper", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({url})
            });
            const data = await response.json();
            if (data.success) {
    result.style.background = "#e8f5e9";
    result.style.border = "1px solid #4caf50";
    let html = '<h3>✅ 成功！</h3>';
    html += '<p>' + data.message + '</p>';
    if (data.customers && data.customers.length > 0) {
        html += '<ul>';
        data.customers.forEach(c => {
            html += '<li>' + c.name + ' (' + c.status + ')</li>';
        });
        html += '</ul>';
    }
    result.innerHTML = html;
}
                result.style.background = "#ffebee";
                result.style.border = "1px solid #f44336";
                result.innerHTML = '<h3>❌ エラー</h3><p>' + data.error + '</p>';
            }
        } catch (err) {
            result.style.background = "#ffebee";
            result.style.border = "1px solid #f44336";
            result.innerHTML = '<h3>❌ エラー</h3><p>' + err.message + '</p>';
        }
    }
    </script>
</body>
</html>"""
    return render_template_string(SCRAPE_TEMPLATE)

@app.route('/export/absences')
@admin_required
def export_absences():
    """欠勤履歴をCSVでエクスポート"""
    absences = load_absences()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['スタッフ名', '欠勤理由', '状況説明', '代替可能日時', '申請日時'])
    for absence in absences:
        writer.writerow([
            absence.get('staff_name', ''),
            absence.get('reason', ''),
            absence.get('details', ''),
            absence.get('alternative_date', ''),
            absence.get('submitted_at', '')[:19].replace('T', ' ')
        ])
    output = si.getvalue()
    si.close()
    response = make_response(output)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename=absences_{datetime.now().strftime("%Y%m%d")}.csv'
    return response

# LINE Webhook - 自動顧客登録（修正版）
@app.route('/webhook', methods=['POST'])
def line_webhook():
    try:
        body = request.get_json()
        events = body.get('events', [])
        
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                message_text = event.get('message', {}).get('text', '')
                
                # メッセージ本文が名前っぽい場合は名前として処理
                if message_text and 2 <= len(message_text) <= 20 and not any(c in message_text for c in ['http', '予約', '確認', 'キャンセル']):
                    # メッセージを名前として登録/更新
                    if save_mapping(message_text, user_id):
                        print(f"✅ 顧客名更新: {message_text} ({user_id})")
                else:
                    # プロフィール取得で新規登録
                    headers = {'Authorization': f'Bearer {LINE_BOT_TOKEN}'}
                    profile_url = f'https://api.line.me/v2/bot/profile/{user_id}'
                    profile_response = requests.get(profile_url, headers=headers)
                    
                    if profile_response.status_code == 200:
                        profile = profile_response.json()
                        display_name = profile.get('displayName', 'Unknown')
                        
                        mapping = load_mapping()
                        if display_name not in mapping:
                            if save_mapping(display_name, user_id):
                                print(f"✅ 新規顧客登録: {display_name} ({user_id})")
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Webhook エラー: {str(e)}")
        return jsonify({'status': 'error'}), 500

# LINE Webhook - スタッフ用
@app.route('/webhook/staff', methods=['POST'])
def line_webhook_staff():
    try:
        body = request.get_json()
        events = body.get('events', [])
        
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                
                # プロフィール取得（スタッフ用トークン使用）
                headers = {'Authorization': f'Bearer {LINE_BOT_TOKEN_STAFF}'}
                profile_url = f'https://api.line.me/v2/bot/profile/{user_id}'
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    display_name = profile.get('displayName', 'Unknown')
                    
                    # 自動登録
                    mapping = load_mapping()
                    if display_name not in mapping:
                        if save_mapping(display_name, user_id):
                            print(f"✅ 新規スタッフ登録: {display_name} ({user_id})")
                        else:
                            print(f"❌ スタッフ登録失敗: {display_name} ({user_id})")
                    else:
                        print(f"[情報] 既に登録済み（スタッフ）: {display_name} ({user_id})")
                else:
                    print(f"❌ プロフィール取得失敗（スタッフ）: status_code={profile_response.status_code}, user_id={user_id}")
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Webhook エラー（スタッフ）: {str(e)}")
        return jsonify({'status': 'error'}), 500


@app.route('/admin/test_http_detailed')
@login_required
@admin_required
def test_http_detailed():
    import requests
    import time
    
    results = []
    
    # ========================================
    # Test 1: 基本的なHTTPリクエスト（タイムアウト60秒）
    # ========================================
    results.append("<h2>Test 1: 基本HTTPリクエスト（タイムアウト60秒）</h2>")
    try:
        start = time.time()
        response = requests.get(
            'https://salonboard.com/login/',
            timeout=180,  # ← 120秒から60秒に変更
            allow_redirects=True
        )
        elapsed = time.time() - start
        results.append(f"✅ <strong>成功</strong>")
        results.append(f"   ステータスコード: {response.status_code}")
        results.append(f"   所要時間: {elapsed:.3f}秒")
        results.append(f"   レスポンスサイズ: {len(response.content)} bytes")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        results.append(f"❌ <strong>失敗</strong>: タイムアウト（60秒）")
        results.append(f"   実際の経過時間: {elapsed:.3f}秒")
    except Exception as e:
        results.append(f"❌ <strong>失敗</strong>: {str(e)}")
    
    # ========================================
    # Test 2: User-Agent追加
    # ========================================
    results.append("<h2>Test 2: User-Agent追加</h2>")
    try:
        start = time.time()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(
            'https://salonboard.com/login/',
            headers=headers,
            timeout=180,  # ← 120秒から60秒に変更
            allow_redirects=True
        )
        elapsed = time.time() - start
        results.append(f"✅ <strong>成功</strong>")
        results.append(f"   ステータスコード: {response.status_code}")
        results.append(f"   所要時間: {elapsed:.3f}秒")
        results.append(f"   レスポンスサイズ: {len(response.content)} bytes")
        results.append(f"   最終URL: {response.url}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        results.append(f"❌ <strong>失敗</strong>: タイムアウト（60秒）")
        results.append(f"   実際の経過時間: {elapsed:.3f}秒")
    except Exception as e:
        results.append(f"❌ <strong>失敗</strong>: {str(e)}")
    
    # ========================================
    # Test 3: ブラウザに近いヘッダー
    # ========================================
    results.append("<h2>Test 3: 完全なブラウザヘッダー</h2>")
    try:
        start = time.time()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(
            'https://salonboard.com/login/',
            headers=headers,
            timeout=180,  # ← 120秒から60秒に変更
            allow_redirects=True
        )
        elapsed = time.time() - start
        results.append(f"✅ <strong>成功</strong>")
        results.append(f"   ステータスコード: {response.status_code}")
        results.append(f"   所要時間: {elapsed:.3f}秒")
        results.append(f"   レスポンスサイズ: {len(response.content)} bytes")
        results.append(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        results.append(f"   Server: {response.headers.get('Server', 'N/A')}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        results.append(f"❌ <strong>失敗</strong>: タイムアウト（60秒）")
        results.append(f"   実際の経過時間: {elapsed:.3f}秒")
    except Exception as e:
        results.append(f"❌ <strong>失敗</strong>: {str(e)}")
    
    # ========================================
    # Test 4: セッション使用（Cookie保持）
    # ========================================
    results.append("<h2>Test 4: セッション使用</h2>")
    try:
        start = time.time()
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        response = session.get(
            'https://salonboard.com/login/',
            timeout=180,  # ← 120秒から60秒に変更
            allow_redirects=True
        )
        elapsed = time.time() - start
        results.append(f"✅ <strong>成功</strong>")
        results.append(f"   ステータスコード: {response.status_code}")
        results.append(f"   所要時間: {elapsed:.3f}秒")
        results.append(f"   Cookie数: {len(response.cookies)}")
        results.append(f"   リダイレクト回数: {len(response.history)}")
    except requests.exceptions.Timeout:
        elapsed = time.time() - start
        results.append(f"❌ <strong>失敗</strong>: タイムアウト（60秒）")
        results.append(f"   実際の経過時間: {elapsed:.3f}秒")
    except Exception as e:
        results.append(f"❌ <strong>失敗</strong>: {str(e)}")
    
    # ========================================
    # 結論
    # ========================================
    results.append("<hr>")
    results.append("<h2>📊 診断結果</h2>")
    results.append("<p>どのテストが成功したかで、問題の原因を特定できます</p>")
    results.append("<ul>")
    results.append("<li>すべて失敗 → SALON BOARDサーバー側の問題</li>")
    results.append("<li>User-Agent追加で成功 → Bot検出の可能性</li>")
    results.append("<li>完全ヘッダーで成功 → ヘッダー不足</li>")
    results.append("<li>セッション使用で成功 → Cookie/セッション管理の問題</li>")
    results.append("</ul>")
    
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>HTTP詳細診断テスト</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                padding: 20px;
                max-width: 900px;
                margin: 0 auto;
                background-color: #f5f5f5;
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #007bff;
                margin-top: 30px;
                border-left: 5px solid #007bff;
                padding-left: 10px;
            }}
            .result {{
                background-color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }}
            a:hover {{
                background-color: #0056b3;
            }}
        </style>
    </head>
    <body>
        <h1>HTTP詳細診断テスト</h1>
        <p>様々な方法でHTTPリクエストを試します（各テスト最大60秒）</p>
        <div class="result">
            {''.join(results)}
        </div>
        <a href="/admin">← 管理画面に戻る</a>
    </body>
    </html>
    """


@app.route('/test_salonboard_login', methods=['GET'])
def test_salonboard_login():
    """SALONBOARD ログインテスト（Firefox使用）"""
    from playwright.sync_api import sync_playwright
    
    try:
        login_id = os.getenv('SALONBOARD_LOGIN_ID')
        password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
        
        if not login_id or not password:
            return jsonify({
                'success': False,
                'error': '環境変数が設定されていません'
            }), 500
        
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            page = browser.new_page()
            page.set_default_timeout(30000)
            
            page.goto('https://salonboard.com/login/')
            page.wait_for_selector('input[name="userId"]', timeout=20000)
            page.fill('input[name="userId"]', login_id)
            page.fill('input[name="password"]', password)
            page.press('input[name="password"]', 'Enter')
            page.wait_for_url('**/KLP/**', timeout=20000)
            
            final_url = page.url
            success = '/KLP/' in final_url
            
            browser.close()
            
            return jsonify({
                'success': success,
                'message': 'ログイン成功' if success else 'ログイン失敗',
                'final_url': final_url,
                'browser': 'firefox',
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'timestamp': datetime.now().isoformat()
        }), 500


# グローバル変数
login_results = {}
login_lock = threading.Lock()

@app.route('/health_check', methods=['GET'])
def health_check():
    """環境確認用"""
    import sys
    return jsonify({
        'status': 'ok',
        'python_version': sys.version,
        'salonboard_id_set': bool(os.getenv('SALONBOARD_LOGIN_ID')),
        'salonboard_pwd_set': bool(os.getenv('SALONBOARD_LOGIN_PASSWORD')),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/test_async', methods=['GET'])
def test_async():
    """subprocess版非同期ログインテスト"""
    import subprocess
    task_id = datetime.now().strftime('%Y%m%d%H%M%S%f')
    
    def bg_login():
        try:
            print(f"[SUBPROCESS] タスク開始: {task_id}", flush=True)
            
            # 完全に独立したプロセスとして実行（180秒タイムアウト）
            result = subprocess.run(
                ['python3', 'salonboard_login.py', task_id],
                capture_output=True,
                text=True,
                timeout=180,
                env=os.environ.copy()
            )
            
            print(f"[SUBPROCESS] stdout: {result.stdout}", flush=True)
            print(f"[SUBPROCESS] stderr: {result.stderr}", flush=True)
            
            # 結果ファイルから読み込み
            result_file = f"/tmp/login_result_{task_id}.json"
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    result_data = json.load(f)
                with login_lock:
                    login_results[task_id] = result_data
                os.remove(result_file)
            else:
                with login_lock:
                    login_results[task_id] = {
                        'success': False,
                        'error': 'Result file not found',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                    
        except subprocess.TimeoutExpired:
            print(f"[SUBPROCESS] タイムアウト（180秒）: {task_id}", flush=True)
            with login_lock:
                login_results[task_id] = {
                    'success': False,
                    'error': 'Subprocess timeout after 180 seconds',
                    'error_type': 'TimeoutExpired'
                }
        except Exception as e:
            print(f"[SUBPROCESS] エラー: {str(e)}", flush=True)
            with login_lock:
                login_results[task_id] = {
                    'success': False,
                    'error': str(e),
                    'error_type': type(e).__name__
                }
    
    threading.Thread(target=bg_login, daemon=True).start()
    return jsonify({
        'status': 'processing',
        'task_id': task_id,
        'check_url': f'/result/{task_id}',
        'message': 'subprocess版ログイン処理を開始しました（タイムアウト180秒）'
    }), 202

@app.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    """結果確認"""
    with login_lock:
        return jsonify(login_results.get(task_id, {'status': 'processing'}))

if __name__ == '__main__':
    # 初期ファイル作成
    if not os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'w') as f:
            json.dump({}, f)
    
    if not os.path.exists(ABSENCE_FILE):
        with open(ABSENCE_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(MESSAGES_FILE):
        default_messages = {
            "absence_request": "{staff_name}が本日欠勤となりました。\n代替出勤が可能でしたら「出勤できます」とメッセージしてください。\n\nよろしくお願いします。",
            "substitute_confirmed": "{substitute_name}が出勤してくれることになりました。\n連絡が入りました。",
            "absence_confirmed": "欠勤申請を受け付けました。\n\n理由: {reason}\n詳細: {details}\n\nご連絡ありがとうございます。\n代替スタッフへの連絡を行いました。無理せずお過ごしください。"
        }
        save_messages(default_messages)
    
    # 24時間ごとにバックアップ
    schedule.every(24).hours.do(backup_customers)
    
    # スケジューラーを別スレッドで開始
    threading.Thread(target=run_scheduler, daemon=True).start()
    
    # 起動時に1回実行
    backup_customers()
    
    print("="*50)
    print("✅ 認証機能付きシステム起動（即時反映対応）")
    print("="*50)
    print("ログインページ: http://localhost:5001/")
    print("\n管理者アカウント:")
    print("  ID: admin / パスワード: admin123")
    print("\nスタッフアカウント:")
    print("  ID: kambara / パスワード: kambara123")
    print("  ID: saori / パスワード: saori123")
    print("="*50)
    
    # Renderの環境変数PORTを使用（ローカルは5001）
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=False, host='0.0.0.0', port=port)

@app.route('/debug/check_files', methods=['GET'])

@app.route('/debug/check_files', methods=['GET'])
def debug_check_files():
    """Dockerコンテナ内のファイル確認"""
    import subprocess
    import os
    
    checks = {}
    
    # 1. カレントディレクトリ
    checks['current_dir'] = os.getcwd()
    
    # 2. salonboard_login.py存在確認
    checks['salonboard_login_exists'] = os.path.exists('salonboard_login.py')
    checks['salonboard_login_path'] = os.path.abspath('salonboard_login.py') if checks['salonboard_login_exists'] else None
    
    # 3. 実行権限確認
    if checks['salonboard_login_exists']:
        checks['salonboard_login_executable'] = os.access('salonboard_login.py', os.X_OK)
        checks['salonboard_login_size'] = os.path.getsize('salonboard_login.py')
    
    # 4. /app ディレクトリ内容
    try:
        checks['app_dir_contents'] = subprocess.run(['ls', '-la', '/app'], capture_output=True, text=True, timeout=5).stdout
    except:
        checks['app_dir_contents'] = 'ERROR'
    
    # 5. Python実行確認
    try:
        checks['python3_version'] = subprocess.run(['python3', '--version'], capture_output=True, text=True, timeout=5).stdout
    except:
        checks['python3_version'] = 'ERROR'
    
    # 6. /tmpへの書き込み確認
    try:
        test_file = '/tmp/test_write.txt'
        with open(test_file, 'w') as f:
            f.write('test')
        checks['tmp_writable'] = os.path.exists(test_file)
        os.remove(test_file)
    except:
        checks['tmp_writable'] = False
    
    # 7. 環境変数確認
    checks['env_salonboard_id'] = bool(os.getenv('SALONBOARD_LOGIN_ID'))
    checks['env_salonboard_pwd'] = bool(os.getenv('SALONBOARD_LOGIN_PASSWORD'))
    
    # 8. メモリ情報
    try:
        checks['memory_info'] = subprocess.run(['free', '-h'], capture_output=True, text=True, timeout=5).stdout
    except:
        checks['memory_info'] = 'ERROR'
    
    # 9. Playwrightブラウザ確認
    try:
        checks['playwright_browsers'] = subprocess.run(['ls', '-la', '/ms-playwright'], capture_output=True, text=True, timeout=5).stdout
    except:
        checks['playwright_browsers'] = 'ERROR'
    
    # 10. salonboard_login.pyの内容（最初の50行）
    if checks['salonboard_login_exists']:
        try:
            with open('salonboard_login.py', 'r') as f:
                checks['salonboard_login_content'] = ''.join(f.readlines()[:50])
        except:
            checks['salonboard_login_content'] = 'ERROR'
    
    return jsonify(checks), 200


@app.route('/debug/test_subprocess', methods=['GET'])
def debug_test_subprocess():
    """subprocessテスト"""
    import subprocess
    
    results = {}
    
    # 1. 単純なコマンド
    try:
        result = subprocess.run(['echo', 'test'], capture_output=True, text=True, timeout=5)
        results['echo_test'] = {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode}
    except Exception as e:
        results['echo_test'] = {'error': str(e)}
    
    # 2. python3テスト
    try:
        result = subprocess.run(['python3', '-c', 'print("hello")'], capture_output=True, text=True, timeout=5)
        results['python3_test'] = {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode}
    except Exception as e:
        results['python3_test'] = {'error': str(e)}
    
    # 3. salonboard_login.py実行テスト（短時間）
    try:
        result = subprocess.run(
            ['python3', 'salonboard_login.py', 'test_debug'],
            capture_output=True,
            text=True,
            timeout=10,
            env=os.environ.copy()
        )
        results['salonboard_login_test'] = {
            'stdout': result.stdout[:1000],
            'stderr': result.stderr[:1000],
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        results['salonboard_login_test'] = {'error': 'Timeout after 10 seconds'}
    except Exception as e:
        results['salonboard_login_test'] = {'error': str(e), 'type': type(e).__name__}
    
    return jsonify(results), 200


@app.route('/debug/test_playwright_import', methods=['GET'])
def debug_test_playwright_import():
    """Playwrightインポートテスト"""
    import subprocess
    
    try:
        result = subprocess.run(
            ['python3', 'test_playwright_import.py'],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy()
        )
        
        return jsonify({
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }), 200
        
    except subprocess.TimeoutExpired as e:
        return jsonify({
            'success': False,
            'error': 'Timeout after 60 seconds',
            'stdout': e.stdout.decode() if e.stdout else '',
            'stderr': e.stderr.decode() if e.stderr else ''
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500


@app.route('/debug/test_salonboard_direct', methods=['GET'])
def debug_test_salonboard_direct():
    """salonboard_login.pyを直接実行"""
    import subprocess
    
    try:
        result = subprocess.run(
            ['python3', 'salonboard_login.py', 'test_render_debug'],
            capture_output=True,
            text=True,
            timeout=300,
            env=os.environ.copy()
        )
        
        return jsonify({
            'success': True,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }), 200
        
    except subprocess.TimeoutExpired as e:
        return jsonify({
            'success': False,
            'error': 'Timeout after 60 seconds',
            'stdout': e.stdout.decode() if e.stdout else '',
            'stderr': e.stderr.decode() if e.stderr else ''
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/api/scrape_today', methods=['GET', 'POST'])
def api_scrape_today():
    """当日予約から電話番号を取得してcustomersに追加"""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'scrape_today.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/scrape_daily_test', methods=['GET', 'POST'])
def scrape_daily_test():
    """テスト用：スクレイピングのみ、LINE送信なし"""
    try:
        import subprocess
        
        result = subprocess.run(
            ['python3', 'scrape_and_upload.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        return jsonify({
            "success": True,
            "scrape_stdout": result.stdout,
            "scrape_stderr": result.stderr,
            "scrape_returncode": result.returncode,
            "note": "テストモード：LINE送信はスキップされました"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/scrape_daily_DISABLED', methods=['GET'])
def scrape_daily():
    """毎日のスクレイピング実行 + リマインド送信"""
    try:
        import subprocess
        
        # 1. スクレイピング実行
        result = subprocess.run(
            ['python3', 'scrape_and_upload.py'],
            capture_output=True,
            text=True,
            timeout=300
        )
        scrape_output = result.stdout
        
        # 2. リマインド送信（テストモード：神原のみ）
        reminder_results = send_reminder_notifications(test_mode=True)
        
        return jsonify({
            "success": True,
            "scrape_stdout": scrape_output,
            "scrape_stderr": result.stderr,
            "scrape_returncode": result.returncode,
            "reminder_results": reminder_results
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def send_reminder_notifications(test_mode=False):
    """3日後・7日後の予約にリマインド通知を送信"""
    import re
    from datetime import datetime, timedelta, timezone
    
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST)
    results = {"3days": {"sent": 0, "failed": 0, "no_match": 0}, "7days": {"sent": 0, "failed": 0, "no_match": 0}}
    
    # テストモード: 神原のみに送信
    KAMBARA_PHONE = "09015992055"
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    # 顧客データを取得
    cust_response = requests.get(f'{SUPABASE_URL}/rest/v1/customers?select=*', headers=headers)
    if cust_response.status_code != 200:
        return {"error": "顧客データ取得失敗"}
    customers = cust_response.json()
    
    # 電話番号→顧客、名前→顧客マッピング
    phone_to_customer = {c['phone']: c for c in customers if c.get('phone')}
    name_to_customer = {}
    for c in customers:
        if c.get('name'):
            normalized = c['name'].replace(" ", "").replace("　", "").replace("★", "").strip()
            name_to_customer[normalized] = c
    
    for days, label in [(3, "3days"), (7, "7days")]:
        target_date = (today + timedelta(days=days))
        target_date_str = target_date.strftime("%Y-%m-%d")
        scrape_date_str = today.strftime("%Y-%m-%d")
        
        # salon_bookingsから該当日の予約を取得
        book_response = requests.get(
            f'{SUPABASE_URL}/rest/v1/salon_bookings?scrape_date=eq.{scrape_date_str}&days_ahead=eq.{days}&select=booking_data&order=id.desc&limit=1',
            headers=headers
        )
        if book_response.status_code != 200:
            continue
        
        result = book_response.json()
        booking_data = result[0].get('booking_data', {}) if result else {}
        bookings = booking_data.get('bookings', []) if isinstance(booking_data, dict) else []
        
        for booking in bookings:
            customer_name = booking.get('お客様名', '').split('\n')[0].replace('★', '').strip()
            phone = booking.get('電話番号', '')
            visit_dt = booking.get('来店日時', '')
            time = re.sub(r'^\d{1,2}/\d{1,2}', '', visit_dt) if visit_dt else ''
            menu = booking.get('メニュー', '')
            
            # 顧客を検索
            customer = None
            if phone and phone in phone_to_customer:
                customer = phone_to_customer[phone]
            else:
                normalized = customer_name.replace(" ", "").replace("　", "").replace("★", "").strip()
                if normalized in name_to_customer:
                    customer = name_to_customer[normalized]
            
            if not customer or not customer.get('line_user_id'):
                results[label]["no_match"] += 1
                continue
            
            # メッセージ作成
            # 日時フォーマット
            def format_dt(dt_str):
                m = re.match(r'(\d+)/(\d+)(\d{2}:\d{2})', dt_str)
                if m:
                    month, day, tm = m.groups()
                    from datetime import date
                    weekdays = ['月', '火', '水', '木', '金', '土', '日']
                    d = date(2025, int(month), int(day))
                    return f"{month}月{day}日({weekdays[d.weekday()]}){tm}〜"
                return dt_str
            
            # メニュークリーンアップ
            def clean_menu(m):
                has_off_shampoo = 'オフあり+アイシャンプー' in m or 'オフあり＋アイシャンプー' in m
                exclude = ['【全員】', '【次回】', '【リピーター様】', '【4週間以内】', '【ご新規】',
                    'オフあり+アイシャンプー', 'オフあり＋アイシャンプー', '次世代まつ毛パーマ', 'ダメージレス',
                    '(4週間以内 )', '(4週間以内)', '(アイシャンプー・トリートメント付き)', '(SP・TR付)',
                    '(コーティング・シャンプー・オフ込)', '(まゆげパーマ)', '(眉毛Wax)', '＋メイク付', '+メイク付',
                    '指名料', 'カラー変更', '束感★']
                for w in exclude:
                    m = m.replace(w, '')
                m = re.sub(r'\(ｸｰﾎﾟﾝ\)', '', m)
                m = re.sub(r'《[^》]*》', '', m)
                m = re.sub(r'【[^】]*】', '', m)
                m = re.sub(r'◇エクステ.*', '', m)
                m = re.sub(r'◇毛量調整.*', '', m)
                m = re.sub(r'[¥￥][0-9,]+', '', m)
                m = re.sub(r'^◇', '', m)
                m = re.sub(r'◇$', '', m)
                m = re.sub(r'◇\s*$', '', m)
                parts = m.split('◇')
                cleaned = [p.strip().strip('　') for p in parts if p.strip()]
                m = '＋'.join(cleaned) if cleaned else ''
                m = re.sub(r'\s+', ' ', m).strip()
                if has_off_shampoo and m:
                    m = f'{m}（オフあり+アイシャンプー）'
                return m
            
            formatted_dt = format_dt(visit_dt)
            cleaned_menu = clean_menu(menu)
            
            if days == 3:
                # テストモード: 神原のみに送信
                KANBARA_PHONE = "09015992055"
                message = f"""{customer_name} 様

ご予約【3日前】のお知らせ🕊️
【本店】
{formatted_dt}
{cleaned_menu}

下記はすべてのお客様に気持ちよくご利用いただくためのご案内です。
ご理解とご協力をお願いいたします🙇‍♀️


■ 遅刻について
スタッフ判断でメニュー変更や日時変更となる場合があり
当日中の時間変更であれば、【次回予約特典】はそのまま適用可能

＜次回予約特典が失効＞
◉予約日から3日前まで
※ご予約日の前倒し・同日時間変更は適用のまま
◉前回来店日から3ヶ月経過

＜キャンセル料＞
◾️次回予約特典
当日変更：施術代金の50％
◾️通常予約
前日変更：施術代金の50％
当日変更：施術代金の100％"""
            else:
                message = f"""{customer_name} 様
ご予約日の【7日前】となりました🕊️
{formatted_dt}
{cleaned_menu}

「マツエクが残っている」
「カールが残っている」
「眉毛の手入れをした…」
「仕事が入った」
など、ご予約日延期は、お早めにご協力をお願いします✨

＜次回予約特典が失効＞
◉予約日から3日前まで
※ご予約日の前倒し・同日時間変更は適用のまま
◉前回来店日から3ヶ月経過

＜キャンセル料＞
◾️次回予約特典
当日変更：施術代金の50％
◾️通常予約
前日変更：施術代金の50％
当日変更：施術代金の100％"""
      
            # 重複送信チェック
            today_str = today.strftime("%Y-%m-%d")
            dup_check = requests.get(
                f'{SUPABASE_URL}/rest/v1/reminder_logs?phone=eq.{phone}&days_ahead=eq.{days}&sent_at=gte.{today_str}T00:00:00',
                headers=headers
            )
            if dup_check.json():
                continue  # 既に今日送信済み
            
            # テストモード: 神原以外はスキップ
            if test_mode and phone != KAMBARA_PHONE:
                continue
            
            # LINE送信
            if send_line_message(customer['line_user_id'], message):
                results[label]["sent"] += 1
                status = "sent"
            else:
                results[label]["failed"] += 1
                status = "failed"
            
            # ログ保存
            requests.post(
                f'{SUPABASE_URL}/rest/v1/reminder_logs',
                headers=headers,
                json={'phone': phone, 'customer_name': customer_name, 'days_ahead': days, 'status': status}
            )
            
            # 神原に送信通知
            if status == "sent":
                notify_message = f"✅ リマインド送信完了\n{customer_name}様（{days}日前）"
                send_line_message("U9022782f05526cf7632902acaed0cb08", notify_message)
    
    return results
# ========== 8週間予約スクレイピング ==========
@app.route('/api/scrape_8weeks', methods=['GET', 'POST'])
def scrape_8weeks():
    """8週間分の予約をスクレイピングしてbookingsテーブルに保存"""
    from datetime import datetime, timedelta, timezone
    from playwright.sync_api import sync_playwright
    import json
    import re
    
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST)
    
    results = {"total": 0, "updated": 0, "errors": []}
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            
            # クッキー読み込み
            cookie_file = os.path.join(os.path.dirname(__file__), 'session_cookies.json')
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
            
            page = context.new_page()
            
            # 8週間分（56日）をループ
            for day_offset in range(56):
                target_date = today + timedelta(days=day_offset)
                date_str = target_date.strftime("%Y%m%d")
                url = f"https://salonboard.com/KLP/reserve/reserveList/?search_date={date_str}"
                
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    
                    # ログインチェック
                    if 'login' in page.url.lower():
                        results["errors"].append(f"ログイン必要: {date_str}")
                        break
                    
                    # 予約データ抽出
                    rows = page.query_selector_all('tr.rsv')
                    
                    for row in rows:
                        try:
                            time_el = row.query_selector('td.time')
                            name_el = row.query_selector('td.name a')
                            phone_el = row.query_selector('td.phone')
                            menu_el = row.query_selector('td.menu')
                            staff_el = row.query_selector('td.staff')
                            
                            visit_time = time_el.inner_text().strip() if time_el else ''
                            customer_name = name_el.inner_text().strip() if name_el else ''
                            phone = phone_el.inner_text().strip() if phone_el else ''
                            menu = menu_el.inner_text().strip() if menu_el else ''
                            staff = staff_el.inner_text().strip() if staff_el else ''
                            
                            if not customer_name:
                                continue
                            
                            # booking_id生成（重複防止用）
                            booking_id = f"{date_str}_{visit_time}_{phone}".replace(" ", "").replace(":", "")
                            
                            data = {
                                'booking_id': booking_id,
                                'customer_name': customer_name.replace('★', '').strip(),
                                'phone': re.sub(r'[^\d]', '', phone),
                                'visit_datetime': f"{target_date.strftime('%m/%d')}{visit_time}",
                                'menu': menu,
                                'staff': staff,
                                'status': 'confirmed',
                                'booking_source': 'salonboard'
                            }
                            
                            # Upsert
                            res = requests.post(
                                f'{SUPABASE_URL}/rest/v1/bookings',
                                headers=headers,
                                json=data
                            )
                            
                            if res.status_code in [200, 201]:
                                results["updated"] += 1
                            
                            results["total"] += 1
                            
                        except Exception as e:
                            continue
                    
                except Exception as e:
                    results["errors"].append(f"{date_str}: {str(e)}")
                    continue
            
            browser.close()
    
    except Exception as e:
        results["errors"].append(str(e))
    
    return jsonify(results)

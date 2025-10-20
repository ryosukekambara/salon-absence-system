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
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Supabase接続を追加（ここから）
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
# supabase = create_client の行は削除
# Supabase接続を追加（ここまで）

LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
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

def save_mapping(customer_name, user_id):
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
        
        if check_response.status_code == 200 and len(check_response.json()) == 0:
            # 新規登録
            data = {
                'name': customer_name,
                'line_user_id': user_id,
                'registered_at': datetime.now().isoformat()
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

def send_line_message(user_id, message, max_retries=3):
    """LINE送信（リトライ＋エラーログ機能付き）"""
    # テストモード：実際に送信しない
    if os.getenv("TEST_MODE", "false").lower() == "true":
        print(f"[テストモード] {user_id[:8]}... → {message[:30]}...")
        return True
    
    if not LINE_BOT_TOKEN:
        print("[エラー] LINE_BOT_TOKENが設定されていません")
        return False
    
    headers = {
        'Authorization': f'Bearer {LINE_BOT_TOKEN}',
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
                <h1>スタッフ管理システム</h1>
                <p>安全で効率的なスタッフ管理</p>
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
                <a href="{{ url_for('logout') }}" class="logout-btn">ログアウト</a>
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
            send_line_message(info['line_id'], absence_message)
    
    # 欠勤スタッフ本人への確認通知
    confirmation_message = MESSAGES["absence_confirmed"].format(
        reason=reason,
        details=details
    )
    send_line_message(STAFF_USERS[staff_name]['line_id'], confirmation_message)
    
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
            .btn { 
                display: inline-block;
                padding: 12px 32px;
                background: #6b5b47;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            }
            .btn:hover {
                background: #8b7355;
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
                <a href="{{ url_for('logout') }}" class="btn">ログアウト</a>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(template)

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
                    
                    if not existing and len(text) >= 2:
                        save_mapping(text, user_id)
                        
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
                
                # プロフィール取得
                headers = {'Authorization': f'Bearer {LINE_BOT_TOKEN}'}
                profile_url = f'https://api.line.me/v2/bot/profile/{user_id}'
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code == 200:
    profile = profile_response.json()
    display_name = profile.get('displayName', 'Unknown')
    # ... 登録処理
else:
    print(f"❌ プロフィール取得失敗: status_code={profile_response.status_code}, user_id={user_id}")
                    
                    # 自動登録
                    mapping = load_mapping()
                    if display_name not in mapping:
                        if save_mapping(display_name, user_id):
                            print(f"✅ 新規顧客登録: {display_name} ({user_id})")
                        else:
                            print(f"❌ 顧客登録失敗: {display_name} ({user_id})")
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Webhook エラー: {str(e)}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
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
    
    app.run(debug=False, host='0.0.0.0', port=5001)
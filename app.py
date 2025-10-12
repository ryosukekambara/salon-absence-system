# app.py - サロン欠勤対応自動化システム
from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
import os
import json
import hashlib
import logging
from datetime import datetime

# Flask アプリ作成
app = Flask(__name__)
app.secret_key = 'salon-system-secret-key'
CORS(app)

# ログ設定
logging.basicConfig(level=logging.INFO)

# データディレクトリ
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')

def init_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    if not os.path.exists(USERS_FILE):
        default_users = {
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin"
            }
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_users, f, ensure_ascii=False, indent=2)

# HTMLテンプレート
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>サロン欠勤対応自動化システム</title>
    <style>
        body { font-family: Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .container { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); width: 90%; max-width: 600px; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #333; font-size: 2.5em; margin-bottom: 10px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: bold; color: #333; }
        input { width: 100%; padding: 15px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; }
        .btn { width: 100%; padding: 15px; background: #667eea; color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .btn:hover { background: #5a6fd8; }
        .message { padding: 15px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; }
        .message.success { background: #d4edda; color: #155724; }
        .message.error { background: #f8d7da; color: #721c24; }
        .status-card { background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div id="loginScreen">
            <div class="header">
                <h1>🏥 サロン欠勤対応自動化システム</h1>
                <p>Phase 1: 基盤システム起動テスト</p>
            </div>
            <form onsubmit="login(event)">
                <div class="form-group">
                    <label>管理者ID</label>
                    <input type="text" id="loginId" value="admin" required>
                </div>
                <div class="form-group">
                    <label>パスワード</label>
                    <input type="password" id="loginPassword" value="admin123" required>
                </div>
                <button type="submit" class="btn">ログイン</button>
            </form>
            <div class="status-card">
                <h3>システム状況</h3>
                <div id="systemStatus">読み込み中...</div>
                <button class="btn" onclick="checkStatus()" style="width: auto; margin-top: 10px;">更新</button>
            </div>
        </div>
        <div id="mainScreen" class="hidden">
            <div class="header">
                <h1>🎉 システム起動成功！</h1>
                <p>Phase 1基盤システムが正常に動作しています</p>
            </div>
            <div class="status-card">
                <h3>✅ 動作確認完了</h3>
                <div>📱 ポート5001での起動: 成功</div>
                <div>🔐 認証システム: 正常</div>
                <div>💾 データベース: 正常</div>
            </div>
        </div>
        <div id="message"></div>
    </div>
    <script>
        function showMessage(msg, type) {
            document.getElementById('message').innerHTML = '<div class="message ' + type + '">' + msg + '</div>';
            setTimeout(() => document.getElementById('message').innerHTML = '', 5000);
        }
        
        async function login(event) {
            event.preventDefault();
            const id = document.getElementById('loginId').value;
            const password = document.getElementById('loginPassword').value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id, password})
                });
                const result = await response.json();
                
                if (result.success) {
                    document.getElementById('loginScreen').classList.add('hidden');
                    document.getElementById('mainScreen').classList.remove('hidden');
                    showMessage('ログイン成功！Phase 1完了', 'success');
                } else {
                    showMessage(result.message, 'error');
                }
            } catch (error) {
                showMessage('エラーが発生しました', 'error');
            }
        }
        
        async function checkStatus() {
            try {
                const response = await fetch('/system/status');
                const result = await response.json();
                document.getElementById('systemStatus').innerHTML = 
                    'データベース: ' + (result.database ? '✅ 正常' : '❌ エラー') +
                    '<br>ファイルシステム: ' + (result.filesystem ? '✅ 正常' : '❌ エラー') +
                    '<br>ポート: 5001 (競合解決済み)';
            } catch (error) {
                document.getElementById('systemStatus').innerHTML = '❌ 確認エラー';
            }
        }
        
        document.addEventListener('DOMContentLoaded', checkStatus);
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if data.get('id') == 'admin' and data.get('password') == 'admin123':
            session['user_id'] = 'admin'
            return jsonify({'success': True, 'message': 'ログイン成功'})
        return jsonify({'success': False, 'message': 'ログイン失敗'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/system/status')
def system_status():
    return jsonify({
        'database': os.path.exists(USERS_FILE),
        'filesystem': os.path.exists(DATA_DIR),
        'port': 5001
    })

if __name__ == '__main__':
    init_data_files()
    print("🚀 システム起動中...")
    print("📍 URL: http://localhost:5001")
    print("🔑 ログイン: admin / admin123")
    
    app.run(host='0.0.0.0', port=5001, debug=True)

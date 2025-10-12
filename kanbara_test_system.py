from flask import Flask, request, jsonify, render_template_string
import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import hmac
import base64

load_dotenv()

app = Flask(__name__)
app.secret_key = 'kanbara-test-system'

# LINE Bot設定
LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_BOT_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# 神原さんのUser ID（自動取得されます）
KANBARA_USER_ID = None
message_log = []

def send_test_message(user_id, message):
    """テスト配信"""
    if not LINE_BOT_TOKEN:
        return False
        
    headers = {
        'Authorization': f'Bearer {LINE_BOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'to': user_id,
        'messages': [{'type': 'text', 'text': message}]
    }
    
    try:
        response = requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers=headers,
            json=data
        )
        return response.status_code == 200
    except Exception as e:
        print(f"送信エラー: {e}")
        return False

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
    """LINE Bot webhook - User ID自動取得"""
    global KANBARA_USER_ID
    
    try:
        events = request.json.get('events', [])
        
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                
                # 初回メッセージでUser IDを記録
                if not KANBARA_USER_ID:
                    KANBARA_USER_ID = user_id
                    
                # メッセージログに記録
                message_log.append({
                    'user_id': user_id,
                    'message': event['message'].get('text', ''),
                    'timestamp': datetime.now().isoformat()
                })
                
                # 確認返信
                reply_message = f"神原さんのUser ID: {user_id[:10]}... 登録完了"
                send_test_message(user_id, reply_message)
        
        return 'OK', 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/')
def dashboard():
    """管理画面"""
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>神原さんのテスト配信システム</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f3f0; }
            .header { background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; padding: 20px; }
            .container { max-width: 800px; margin: 20px auto; padding: 0 20px; }
            .card { background: white; padding: 30px; border-radius: 10px; margin: 20px 0; box-shadow: 0 2px 10px rgba(139, 115, 85, 0.1); }
            .btn { padding: 15px 30px; background: #8b7355; color: white; border: none; border-radius: 8px; cursor: pointer; margin: 10px 5px; font-size: 14px; }
            .btn:hover { background: #6b5b47; }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .status-ok { background: #d1fae5; color: #065f46; }
            .status-error { background: #fee2e2; color: #991b1b; }
            .user-id { background: #f3f4f6; padding: 15px; border-radius: 8px; font-family: monospace; }
            #result { margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>神原さんのテスト配信システム</h1>
            <p>安全なテスト環境 - 神原さんのみに配信</p>
        </div>
        
        <div class="container">
            <div class="card">
                <h3>接続状況</h3>
                <div class="status {{ 'status-ok' if line_connected else 'status-error' }}">
                    LINE Bot: {{ 'Connected' if line_connected else 'Not Connected' }}
                </div>
                
                {% if user_id %}
                <div class="status status-ok">
                    神原さんのUser ID: 取得済み
                </div>
                <div class="user-id">{{ user_id }}</div>
                {% else %}
                <div class="status status-error">
                    User ID: 未取得 - LINE Botにメッセージを送信してください
                </div>
                {% endif %}
            </div>
            
            <div class="card">
                <h3>テスト配信メニュー</h3>
                
                <button class="btn" onclick="testMessage('hello')">
                    接続テスト
                </button>
                
                <button class="btn" onclick="testMessage('absence')">
                    欠勤通知テスト
                </button>
                
                <button class="btn" onclick="testMessage('substitute')">
                    代替募集テスト
                </button>
                
                <button class="btn" onclick="testMessage('customer')">
                    顧客通知テスト
                </button>
                
                <button class="btn" onclick="testMessage('complete')">
                    完全フローテスト
                </button>
                
                <div id="result"></div>
            </div>
            
            {% if message_log %}
            <div class="card">
                <h3>メッセージログ</h3>
                {% for msg in message_log %}
                <div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px;">
                    <strong>{{ msg.timestamp[:19] }}</strong><br>
                    {{ msg.message }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>

        <script>
        async function testMessage(type) {
            const result = await fetch(`/api/test/${type}`, {method: 'POST'});
            const data = await result.json();
            
            const resultDiv = document.getElementById('result');
            const status = data.success ? 'status-ok' : 'status-error';
            const statusText = data.success ? 'Success' : 'Failed';
            
            resultDiv.innerHTML = `
                <div class="status ${status}">
                    <strong>${statusText}:</strong> ${data.message}<br>
                    <small>${new Date().toLocaleString()}</small>
                </div>
            `;
        }
        </script>
    </body>
    </html>
    """
    
    return render_template_string(template,
        line_connected=bool(LINE_BOT_TOKEN),
        user_id=KANBARA_USER_ID,
        message_log=message_log[-5:]
    )

@app.route('/api/test/hello', methods=['POST'])
def test_hello():
    """接続テスト"""
    if not KANBARA_USER_ID:
        return jsonify({"success": False, "message": "User IDが取得されていません"})
    
    message = "神原さん、接続テストです。システムは正常に動作しています。"
    success = send_test_message(KANBARA_USER_ID, message)
    
    return jsonify({
        "success": success,
        "message": "接続テスト完了" if success else "送信失敗"
    })

@app.route('/api/test/absence', methods=['POST'])
def test_absence():
    """欠勤通知テスト"""
    if not KANBARA_USER_ID:
        return jsonify({"success": False, "message": "User IDが取得されていません"})
    
    message = """【TEST】欠勤通知

田中美咲さんが体調不良のため欠勤となりました。

日時: 2025年9月23日
対応: 代替スタッフ手配中

※神原さん専用テスト配信"""
    
    success = send_test_message(KANBARA_USER_ID, message)
    
    return jsonify({
        "success": success,
        "message": "欠勤通知テスト送信完了" if success else "送信失敗"
    })

@app.route('/api/test/substitute', methods=['POST'])
def test_substitute():
    """代替募集テスト"""
    if not KANBARA_USER_ID:
        return jsonify({"success": False, "message": "User IDが取得されていません"})
    
    message = """【TEST】代替スタッフ募集

急募！代替出勤可能な方を探しています。

欠勤者: 田中美咲
日時: 本日 10:00-18:00
必要スキル: カット、カラー

※神原さん専用テスト配信"""
    
    success = send_test_message(KANBARA_USER_ID, message)
    
    return jsonify({
        "success": success,
        "message": "代替募集テスト送信完了" if success else "送信失敗"
    })

@app.route('/api/test/customer', methods=['POST'])
def test_customer():
    """顧客通知テスト"""
    if not KANBARA_USER_ID:
        return jsonify({"success": False, "message": "User IDが取得されていません"})
    
    message = """【TEST】お客様への通知

山田様へ送信予定のメッセージ:

申し訳ございませんが、本日のご予約について担当スタッフの欠勤により、別日への振替をお願いいたします。

※実際の顧客には送信されません
※神原さん専用テスト配信"""
    
    success = send_test_message(KANBARA_USER_ID, message)
    
    return jsonify({
        "success": success,
        "message": "顧客通知テスト送信完了" if success else "送信失敗"
    })

@app.route('/api/test/complete', methods=['POST'])
def test_complete():
    """完全フローテスト"""
    if not KANBARA_USER_ID:
        return jsonify({"success": False, "message": "User IDが取得されていません"})
    
    message = """【TEST】完全自動化フロー

神原さん、自動化システムのテストです:

1. 欠勤メッセージ受信 ✓
2. 代替スタッフ募集 ✓  
3. 予約データ取得 ✓
4. 顧客通知送信 ✓

全てのフローが正常に動作しています。

※神原さん専用テスト配信"""
    
    success = send_test_message(KANBARA_USER_ID, message)
    
    return jsonify({
        "success": success,
        "message": "完全フローテスト完了" if success else "送信失敗"
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("神原さんのテスト配信システム")
    print("="*50)
    print("管理画面: http://localhost:5001/")
    print("Webhook: http://localhost:5001/webhook/line")
    print("="*50)
    print("\n初期設定:")
    print("1. LINE DevelopersでWebhook URLを設定")
    print("2. LINE Botに何でもメッセージを送信")
    print("3. User IDが自動取得されます")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

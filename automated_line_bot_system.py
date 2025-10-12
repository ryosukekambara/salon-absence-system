from flask import Flask, request, jsonify, render_template_string, redirect, session
from datetime import datetime, timedelta
import json
import re
import requests
from dotenv import load_dotenv
import os
import hashlib
import hmac
import base64

load_dotenv()

app = Flask(__name__)
app.secret_key = 'automated-salon-system-2025'

# LINE Bot設定
LINE_CHANNEL_ACCESS_TOKEN_A = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')  # スタッフ用Bot
LINE_CHANNEL_SECRET_A = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN_B = "CUSTOMER_BOT_TOKEN"  # 顧客用Bot (別途設定)

# データストレージ
staff_data = {
    "田中美咲": {"user_id": "U001", "skills": ["カット", "カラー"], "phone": "090-1111-1111"},
    "佐藤花子": {"user_id": "U002", "skills": ["パーマ", "トリートメント"], "phone": "090-2222-2222"},
    "鈴木太郎": {"user_id": "U003", "skills": ["カット", "基本"], "phone": "090-3333-3333"}
}

absence_logs = []
substitute_requests = []
customer_notifications = []

# メッセージ解析パターン
ABSENCE_PATTERNS = [
    r'(欠勤|休み|休む|当日欠勤|体調不良|発熱|急用)',
    r'(今日.*?(出勤できない|来れない|いけない))',
    r'(すみません.*?(休ませて|欠勤))'
]

SUBSTITUTE_PATTERNS = [
    r'(代わり|代理|出勤|ヘルプ|お願い)',
    r'(カバー|フォロー|代替)',
    r'(出れる|出られる|可能|大丈夫)'
]

def analyze_message(text):
    """メッセージを解析してトリガーを検出"""
    text = text.replace('\n', '').replace(' ', '')
    
    # 欠勤メッセージの検出
    for pattern in ABSENCE_PATTERNS:
        if re.search(pattern, text):
            return {"type": "absence", "confidence": 0.9}
    
    # 代替申出メッセージの検出  
    for pattern in SUBSTITUTE_PATTERNS:
        if re.search(pattern, text):
            return {"type": "substitute_offer", "confidence": 0.8}
    
    return {"type": "unknown", "confidence": 0.0}

def send_line_message(access_token, user_id, message):
    """LINE メッセージ送信"""
    headers = {
        'Authorization': f'Bearer {access_token}',
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
    except:
        return False

def broadcast_substitute_request(absent_staff, date, reason):
    """代替スタッフへの一斉通知"""
    message = f"""
📢 代替スタッフ募集

欠勤者: {absent_staff}
日付: {date}
理由: {reason}

出勤可能な方は「代わります」とメッセージしてください。
    """.strip()
    
    # 欠勤者以外の全スタッフに送信
    for name, data in staff_data.items():
        if name != absent_staff:
            send_line_message(LINE_CHANNEL_ACCESS_TOKEN_A, data['user_id'], message)

def scrape_customer_appointments(staff_name, date):
    """顧客予約データのスクレイピング（デモ版）"""
    # 実際の実装では、サロンボードやPOSシステムから取得
    demo_appointments = [
        {"customer": "山田太郎", "time": "10:00", "service": "カット", "phone": "090-1111-1111"},
        {"customer": "佐々木花子", "time": "14:00", "service": "カラー", "phone": "090-2222-2222"},
        {"customer": "田中一郎", "time": "16:00", "service": "パーマ", "phone": "090-3333-3333"}
    ]
    
    return demo_appointments

def notify_customers_auto(appointments, absent_staff, date):
    """顧客への自動通知"""
    for appointment in appointments:
        message = f"""
【重要】予約変更のお願い

{appointment['customer']}様

申し訳ございませんが、{date}の{appointment['time']}からのご予約について、担当スタッフ（{absent_staff}）が急遽欠勤となりました。

別日への振替をお願いいたします。
ご迷惑をおかけし、大変申し訳ございません。

振替希望日をお聞かせください。
        """.strip()
        
        # 実際の実装では、顧客用LINE Bot Bに送信
        customer_notifications.append({
            "customer": appointment['customer'],
            "message": message,
            "status": "sent",
            "timestamp": datetime.now().isoformat()
        })

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
    """LINE Bot Aのwebhook"""
    
    # 署名検証
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    # 実際の実装では署名検証を実装
    # if not validate_signature(body, signature):
    #     return 'Invalid signature', 400
    
    try:
        events = request.json.get('events', [])
        
        for event in events:
            if event['type'] == 'message' and event['message']['type'] == 'text':
                user_id = event['source']['userId']
                message_text = event['message']['text']
                
                # スタッフ特定（実際の実装では、user_idとスタッフのマッピングテーブル使用）
                staff_name = None
                for name, data in staff_data.items():
                    if data['user_id'] == user_id:
                        staff_name = name
                        break
                
                if not staff_name:
                    continue
                
                # メッセージ解析
                analysis = analyze_message(message_text)
                
                if analysis['type'] == 'absence':
                    # 欠勤処理フロー
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    absence_record = {
                        "id": f"abs_{len(absence_logs)+1:03d}",
                        "staff_name": staff_name,
                        "user_id": user_id,
                        "date": today,
                        "reason": "体調不良",
                        "original_message": message_text,
                        "created_at": datetime.now().isoformat(),
                        "status": "processing"
                    }
                    absence_logs.append(absence_record)
                    
                    # 確認メッセージ
                    reply_message = f"承知いたしました。{staff_name}さんの欠勤を登録しました。代替スタッフを手配いたします。"
                    send_line_message(LINE_CHANNEL_ACCESS_TOKEN_A, user_id, reply_message)
                    
                    # 代替スタッフへの一斉通知
                    broadcast_substitute_request(staff_name, today, "急遽欠勤")
                    
                    # 顧客予約データ取得
                    appointments = scrape_customer_appointments(staff_name, today)
                    
                    # 顧客への自動通知
                    notify_customers_auto(appointments, staff_name, today)
                    
                elif analysis['type'] == 'substitute_offer':
                    # 代替申出処理
                    substitute_record = {
                        "id": f"sub_{len(substitute_requests)+1:03d}",
                        "substitute_staff": staff_name,
                        "user_id": user_id,
                        "message": message_text,
                        "created_at": datetime.now().isoformat(),
                        "status": "offered"
                    }
                    substitute_requests.append(substitute_record)
                    
                    # 確認メッセージ
                    reply_message = f"{staff_name}さん、代替出勤のご協力ありがとうございます。詳細をお送りします。"
                    send_line_message(LINE_CHANNEL_ACCESS_TOKEN_A, user_id, reply_message)
        
        return 'OK', 200
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/')
def admin_dashboard():
    """管理画面"""
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>自動化サロン管理システム</title>
        <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
        <style>
            body { font-family: 'Hiragino Sans', Arial, sans-serif; margin: 0; padding: 0; background: #f5f3f0; }
            .header { background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(139, 115, 85, 0.1); }
            .stat { font-size: 2em; font-weight: bold; color: #8b7355; }
            .log-item { background: #f8f6f3; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 4px solid #8b7355; }
            .status-active { color: #22c55e; }
            .status-pending { color: #f59e0b; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🤖 自動化サロン管理システム</h1>
            <p>LINE Bot自動処理 - リアルタイム監視</p>
        </div>
        
        <div class="container">
            <div class="grid">
                <div class="card">
                    <h3>📊 システム状況</h3>
                    <div class="stat">{{ absence_count }}</div>
                    <p>処理済み欠勤</p>
                    <div class="stat">{{ substitute_count }}</div>
                    <p>代替申出</p>
                    <div class="stat">{{ notification_count }}</div>
                    <p>顧客通知送信</p>
                </div>
                
                <div class="card">
                    <h3>⚡ 自動化フロー</h3>
                    <div>✅ LINE Bot A受信</div>
                    <div>✅ メッセージ解析</div>
                    <div>✅ トリガー検出</div>
                    <div>✅ 代替スタッフ通知</div>
                    <div>✅ 予約データ取得</div>
                    <div>✅ 顧客自動通知</div>
                </div>
                
                <div class="card">
                    <h3>📝 最新の欠勤ログ</h3>
                    {% for absence in recent_absences %}
                    <div class="log-item">
                        <strong>{{ absence.staff_name }}</strong><br>
                        日付: {{ absence.date }}<br>
                        時刻: {{ absence.created_at[:19] }}<br>
                        <span class="status-active">自動処理完了</span>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="card">
                    <h3>🙋 代替申出ログ</h3>
                    {% for substitute in recent_substitutes %}
                    <div class="log-item">
                        <strong>{{ substitute.substitute_staff }}</strong><br>
                        時刻: {{ substitute.created_at[:19] }}<br>
                        <span class="status-pending">調整中</span>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="card">
                    <h3>📞 顧客通知ログ</h3>
                    {% for notification in recent_notifications %}
                    <div class="log-item">
                        {{ notification.customer }}<br>
                        <span class="status-active">送信完了</span><br>
                        {{ notification.timestamp[:19] }}
                    </div>
                    {% endfor %}
                </div>
                
                <div class="card">
                    <h3>🔧 システム設定</h3>
                    <p>Webhook URL: /webhook/line</p>
                    <p>LINE Bot A: 
                        <span class="status-active">接続中</span>
                    </p>
                    <p>LINE Bot B: 
                        <span class="status-pending">設定待ち</span>
                    </p>
                    <p>自動処理: 
                        <span class="status-active">有効</span>
                    </p>
                </div>
            </div>
        </div>

        <script>lucide.createIcons();</script>
    </body>
    </html>
    """
    
    return render_template_string(template,
        absence_count=len(absence_logs),
        substitute_count=len(substitute_requests),
        notification_count=len(customer_notifications),
        recent_absences=absence_logs[-3:],
        recent_substitutes=substitute_requests[-3:],
        recent_notifications=customer_notifications[-3:]
    )

@app.route('/api/test/flow', methods=['POST'])
def test_automated_flow():
    """自動化フローのテスト"""
    
    # デモ欠勤メッセージのシミュレーション
    test_message = "体調不良のため、今日欠勤させていただきます"
    staff_name = "田中美咲"
    
    # メッセージ解析テスト
    analysis = analyze_message(test_message)
    
    if analysis['type'] == 'absence':
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 欠勤登録
        absence_record = {
            "id": f"test_{len(absence_logs)+1:03d}",
            "staff_name": staff_name,
            "date": today,
            "reason": "体調不良",
            "original_message": test_message,
            "created_at": datetime.now().isoformat(),
            "status": "test_processed"
        }
        absence_logs.append(absence_record)
        
        # 顧客予約データ取得（デモ）
        appointments = scrape_customer_appointments(staff_name, today)
        
        # 顧客通知（デモ）
        notify_customers_auto(appointments, staff_name, today)
        
        return jsonify({
            "status": "success",
            "message": "自動化フローテスト完了",
            "processed": {
                "absence_registered": absence_record,
                "appointments_found": len(appointments),
                "notifications_sent": len(appointments)
            }
        })
    
    return jsonify({"status": "error", "message": "メッセージ解析失敗"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🤖 自動化サロン管理システム - LINE Bot統合版")
    print("="*60)
    print("📍 管理画面: http://localhost:5001/")
    print("📍 Webhook: http://localhost:5001/webhook/line")
    print("🔗 フローテスト: POST /api/test/flow")
    print("\n⚡ 自動化機能:")
    print("1. LINE Bot A → メッセージ受信・解析")
    print("2. 欠勤検出 → 代替スタッフ一斉通知")
    print("3. 予約データ自動取得")
    print("4. LINE Bot B → 顧客自動通知")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

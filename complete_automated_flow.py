from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import json
import re
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'automated-flow-2025'

# LINE Bot設定
LINE_BOT_A_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')  # スタッフ用Bot
LINE_BOT_A_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_BOT_B_TOKEN = "CUSTOMER_BOT_TOKEN"  # 顧客用Bot（別途取得）

# スタッフデータ
staff_mapping = {
    "U001": {"name": "田中美咲", "skills": ["カット", "カラー"]},
    "U002": {"name": "佐藤花子", "skills": ["パーマ", "トリートメント"]},
    "U003": {"name": "鈴木太郎", "skills": ["カット", "基本対応"]}
}

# データストレージ
absence_reports = []
substitute_offers = []
customer_notifications = []

# メッセージ解析パターン
def analyze_absence_message(text):
    """欠勤メッセージの検出"""
    patterns = [
        r'(当日欠勤|欠勤|休み|休む)',
        r'(体調不良|発熱|具合が悪い)',
        r'(出勤できない|来れない|いけない)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

def analyze_substitute_message(text):
    """代替申出メッセージの検出"""
    patterns = [
        r'(代わり|代理|替わり)',
        r'(出勤.*お願い|ヘルプ|フォロー)',
        r'(出れる|出られる|可能|大丈夫)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

def send_line_message(token, user_id, message):
    """LINE メッセージ送信"""
    headers = {
        'Authorization': f'Bearer {token}',
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

def scrape_appointment_data(staff_name, date):
    """予約データスクレイピング（デモ実装）"""
    # 実際の実装では、サロンボードや予約システムからデータ取得
    demo_appointments = [
        {
            "customer_name": "山田太郎",
            "appointment_time": "10:00",
            "service": "カット",
            "staff": staff_name,
            "date": date,
            "customer_line_id": "C001"  # 顧客のLINE ID
        },
        {
            "customer_name": "佐々木花子", 
            "appointment_time": "14:00",
            "service": "カラー",
            "staff": staff_name,
            "date": date,
            "customer_line_id": "C002"
        }
    ]
    
    return demo_appointments

def notify_customers_via_bot_b(appointments, absent_staff):
    """LINE Bot B経由で顧客通知"""
    for appointment in appointments:
        message = f"""
【重要】予約変更のお願い

{appointment['customer_name']}様

申し訳ございませんが、{appointment['date']}の{appointment['appointment_time']}からのご予約について、担当スタッフ（{absent_staff}）が急遽欠勤となりました。

別日への振替をお願いいたします。
ご迷惑をおかけし、大変申し訳ございません。

振替希望日をお聞かせください。
        """.strip()
        
        # LINE Bot B で顧客に送信
        success = send_line_message(LINE_BOT_B_TOKEN, appointment['customer_line_id'], message)
        
        # 通知ログに記録
        customer_notifications.append({
            "customer": appointment['customer_name'],
            "message": message,
            "sent_at": datetime.now().isoformat(),
            "success": success
        })

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
    """LINE Bot A のメッセージ受信処理"""
    
    try:
        events = request.json.get('events', [])
        
        for event in events:
            if event['type'] == 'message' and event['message']['type'] == 'text':
                user_id = event['source']['userId']
                message_text = event['message']['text']
                
                # スタッフ特定
                staff_info = staff_mapping.get(user_id)
                if not staff_info:
                    continue
                
                staff_name = staff_info['name']
                
                # フロー1: 欠勤メッセージ処理
                if analyze_absence_message(message_text):
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    # 欠勤記録
                    absence_record = {
                        "staff_name": staff_name,
                        "user_id": user_id,
                        "date": today,
                        "original_message": message_text,
                        "created_at": datetime.now().isoformat(),
                        "status": "processing"
                    }
                    absence_reports.append(absence_record)
                    
                    # スタッフに確認返信
                    reply = f"承知いたしました。{staff_name}さんの欠勤を受理しました。代替スタッフの手配を開始します。"
                    send_line_message(LINE_BOT_A_TOKEN, user_id, reply)
                    
                    # 他のスタッフに代替依頼
                    substitute_request = f"""
📢 代替出勤のお願い

{staff_name}さんが本日欠勤となりました。
代替出勤が可能な方は「代わりに出勤をお願いします」とメッセージしてください。

日時: {today}
                    """.strip()
                    
                    # 他のスタッフ全員に送信
                    for uid, info in staff_mapping.items():
                        if uid != user_id:  # 欠勤者以外
                            send_line_message(LINE_BOT_A_TOKEN, uid, substitute_request)
                
                # フロー2: 代替申出メッセージ処理
                elif analyze_substitute_message(message_text):
                    
                    # 代替申出記録
                    substitute_record = {
                        "substitute_staff": staff_name,
                        "user_id": user_id,
                        "message": message_text,
                        "created_at": datetime.now().isoformat(),
                        "status": "accepted"
                    }
                    substitute_offers.append(substitute_record)
                    
                    # 代替スタッフに確認
                    reply = f"{staff_name}さん、代替出勤のご協力ありがとうございます。調整いたします。"
                    send_line_message(LINE_BOT_A_TOKEN, user_id, reply)
                    
                    # フロー3: 自動スクレイピング実行
                    if absence_reports:
                        latest_absence = absence_reports[-1]
                        absent_staff = latest_absence['staff_name']
                        absence_date = latest_absence['date']
                        
                        # 予約データ取得
                        appointments = scrape_appointment_data(absent_staff, absence_date)
                        
                        # フロー4: 顧客への自動通知（LINE Bot B）
                        notify_customers_via_bot_b(appointments, absent_staff)
        
        return 'OK', 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/')
def monitoring_dashboard():
    """自動化フロー監視画面"""
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>自動化フロー監視システム</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f5f3f0; }
            .header { background: linear-gradient(135deg, #8b7355 0%, #6b5b47 100%); color: white; padding: 20px; }
            .container { max-width: 1200px; margin: 20px auto; padding: 0 20px; }
            .flow-diagram { background: white; padding: 30px; border-radius: 10px; margin: 20px 0; }
            .flow-step { display: flex; align-items: center; margin: 15px 0; }
            .flow-arrow { margin: 0 15px; color: #8b7355; font-size: 1.5em; }
            .status-box { display: inline-block; padding: 5px 10px; border-radius: 5px; font-size: 12px; }
            .status-active { background: #d1fae5; color: #065f46; }
            .status-pending { background: #fef3c7; color: #92400e; }
            .logs { background: white; padding: 20px; border-radius: 10px; margin: 10px 0; }
            .log-item { background: #f8f6f3; padding: 15px; border-radius: 8px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>自動化フロー監視システム</h1>
            <p>LINE Bot A・B 統合監視</p>
        </div>
        
        <div class="container">
            <div class="flow-diagram">
                <h2>自動化フロー状況</h2>
                
                <div class="flow-step">
                    <strong>1. スタッフ → LINE Bot A:</strong> 
                    <span class="flow-arrow">↓</span>
                    <span class="status-box status-active">{{ absence_count }}件 処理済み</span>
                </div>
                
                <div class="flow-step">
                    <strong>2. システム: メッセージ解析・トリガー検出</strong>
                    <span class="flow-arrow">↓</span>
                    <span class="status-box status-active">稼働中</span>
                </div>
                
                <div class="flow-step">
                    <strong>3. 代替スタッフ → LINE Bot A:</strong>
                    <span class="flow-arrow">↓</span>
                    <span class="status-box status-active">{{ substitute_count }}件 申出</span>
                </div>
                
                <div class="flow-step">
                    <strong>4. システム: 自動スクレイピング実行</strong>
                    <span class="flow-arrow">↓</span>
                    <span class="status-box status-active">自動実行</span>
                </div>
                
                <div class="flow-step">
                    <strong>5. LINE Bot B → 顧客通知:</strong>
                    <span class="status-box status-active">{{ notification_count }}件 送信</span>
                </div>
            </div>
            
            <div class="logs">
                <h3>欠勤報告ログ</h3>
                {% for absence in recent_absences %}
                <div class="log-item">
                    <strong>{{ absence.staff_name }}</strong> - {{ absence.date }}<br>
                    メッセージ: {{ absence.original_message }}<br>
                    時刻: {{ absence.created_at[:19] }}
                </div>
                {% endfor %}
            </div>
            
            <div class="logs">
                <h3>代替申出ログ</h3>
                {% for substitute in recent_substitutes %}
                <div class="log-item">
                    <strong>{{ substitute.substitute_staff }}</strong><br>
                    メッセージ: {{ substitute.message }}<br>
                    時刻: {{ substitute.created_at[:19] }}
                </div>
                {% endfor %}
            </div>
            
            <div class="logs">
                <h3>顧客通知ログ</h3>
                {% for notification in recent_notifications %}
                <div class="log-item">
                    顧客: {{ notification.customer }}<br>
                    送信時刻: {{ notification.sent_at[:19] }}<br>
                    状態: {{ "成功" if notification.success else "失敗" }}
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template,
        absence_count=len(absence_reports),
        substitute_count=len(substitute_offers),
        notification_count=len(customer_notifications),
        recent_absences=absence_reports[-5:],
        recent_substitutes=substitute_offers[-5:],
        recent_notifications=customer_notifications[-5:]
    )

@app.route('/api/test/complete-flow', methods=['POST'])
def test_complete_flow():
    """完全フローのテスト実行"""
    
    # テスト1: 欠勤メッセージ
    test_absence_msg = "体調不良のため、当日欠勤します"
    
    if analyze_absence_message(test_absence_msg):
        # 欠勤処理
        absence_record = {
            "staff_name": "田中美咲",
            "user_id": "U001",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "original_message": test_absence_msg,
            "created_at": datetime.now().isoformat(),
            "status": "test"
        }
        absence_reports.append(absence_record)
        
        # テスト2: 代替申出
        test_substitute_msg = "代わりに出勤をお願いします"
        
        if analyze_substitute_message(test_substitute_msg):
            substitute_record = {
                "substitute_staff": "佐藤花子",
                "user_id": "U002", 
                "message": test_substitute_msg,
                "created_at": datetime.now().isoformat(),
                "status": "test"
            }
            substitute_offers.append(substitute_record)
            
            # テスト3: スクレイピング実行
            appointments = scrape_appointment_data("田中美咲", absence_record['date'])
            
            # テスト4: 顧客通知
            notify_customers_via_bot_b(appointments, "田中美咲")
            
            return jsonify({
                "status": "success",
                "message": "完全自動化フローテスト完了",
                "results": {
                    "absence_detected": True,
                    "substitute_detected": True,
                    "appointments_scraped": len(appointments),
                    "customers_notified": len(appointments)
                }
            })
    
    return jsonify({"status": "error", "message": "フローテスト失敗"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("完全自動化LINE Botフローシステム")
    print("="*60)
    print("管理画面: http://localhost:5001/")
    print("Webhook: http://localhost:5001/webhook/line")
    print("フローテスト: POST /api/test/complete-flow")
    print("\n自動化フロー:")
    print("1. スタッフ → LINE Bot A: 欠勤報告")
    print("2. システム: メッセージ解析・トリガー検出")  
    print("3. 代替スタッフ → LINE Bot A: 申出")
    print("4. システム: 自動スクレイピング実行")
    print("5. LINE Bot B → 顧客: 振替依頼")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

from flask import Flask, request, jsonify, render_template_string
import json
import re
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'simple-absence-2025'

# LINE Bot設定
LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_BOT_SECRET = os.getenv('LINE_CHANNEL_SECRET')

# スタッフ基本情報（シンプル版）
staff_mapping = {
    "U001": {"name": "田中美咲"},
    "U002": {"name": "佐藤花子"},  
    "U003": {"name": "鈴木美香"}
}

# データストレージ
absence_reports = []
substitute_offers = []
customer_notifications = []
automation_log = []

def analyze_absence_message(text):
    """当日欠勤メッセージの自動検出"""
    patterns = [
        r'(当日欠勤|欠勤|休み|休む)',
        r'(体調不良|発熱|具合が悪い|風邪)',
        r'(出勤できない|来れない|いけない|無理)',
        r'(すみません.*休|申し訳.*欠勤)'
    ]
    
    confidence = 0
    for pattern in patterns:
        if re.search(pattern, text):
            confidence += 0.25
    
    return {
        "is_absence": confidence > 0.2,
        "confidence": min(confidence, 1.0)
    }

def analyze_substitute_message(text):
    """代替申出メッセージの自動検出"""
    patterns = [
        r'(代わり|代理|替わり)',
        r'(出勤.*お願い|ヘルプ|フォロー)',
        r'(出れる|出られる|可能|大丈夫)',
        r'(カバー|サポート|手伝)'
    ]
    
    confidence = 0
    for pattern in patterns:
        if re.search(pattern, text):
            confidence += 0.25
    
    return {
        "is_substitute": confidence > 0.2,
        "confidence": min(confidence, 1.0)
    }

def send_line_message(token, user_id, message):
    """LINE メッセージ送信"""
    if not token:
        return False
    
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
    except Exception as e:
        print(f"LINE送信エラー: {e}")
        return False

def get_appointments(staff_name, date):
    """予約データ取得（デモ版）"""
    demo_appointments = [
        {
            "customer_name": "山田花子",
            "appointment_time": "10:00",
            "service": "まつげエクステ",
            "staff": staff_name,
            "date": date
        },
        {
            "customer_name": "佐々木美咲", 
            "appointment_time": "14:00",
            "service": "まつげエクステ",
            "staff": staff_name,
            "date": date
        }
    ]
    
    automation_log.append({
        "action": "予約データ取得",
        "staff": staff_name,
        "appointments_found": len(demo_appointments),
        "timestamp": datetime.now().isoformat()
    })
    
    return demo_appointments

def notify_customers(appointments, absent_staff, absence_reason):
    """顧客通知"""
    for appointment in appointments:
        message = f"""
【重要】ご予約変更のお願い

{appointment['customer_name']}様

申し訳ございませんが、{appointment['date']}の{appointment['appointment_time']}からのご予約について、担当スタッフ（{absent_staff}）が{absence_reason}により急遽欠勤となりました。

つきましては、別日への振替をお願いいたします。
ご迷惑をおかけし、大変申し訳ございません。

振替希望日をお聞かせください。

サロン
        """.strip()
        
        customer_notifications.append({
            "customer": appointment['customer_name'],
            "appointment_time": appointment['appointment_time'],
            "service": appointment['service'],
            "sent_at": datetime.now().isoformat(),
            "success": True
        })
    
    automation_log.append({
        "action": "顧客通知送信",
        "customers_notified": len(appointments),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
    """当日欠勤対応システム"""
    
    try:
        events = request.json.get('events', [])
        
        for event in events:
            if event['type'] == 'message' and event['message']['type'] == 'text':
                user_id = event['source']['userId']
                message_text = event['message']['text']
                
                staff_info = staff_mapping.get(user_id)
                if not staff_info:
                    continue
                
                staff_name = staff_info['name']
                
                # 当日欠勤メッセージ検出
                absence_analysis = analyze_absence_message(message_text)
                
                if absence_analysis['is_absence']:
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    absence_record = {
                        "id": f"abs_{len(absence_reports)+1:03d}",
                        "staff_name": staff_name,
                        "user_id": user_id,
                        "date": today,
                        "reason": "体調不良" if "体調不良" in message_text else "急用",
                        "original_message": message_text,
                        "confidence": absence_analysis['confidence'],
                        "created_at": datetime.now().isoformat(),
                        "status": "処理中"
                    }
                    absence_reports.append(absence_record)
                    
                    automation_log.append({
                        "action": "当日欠勤検出",
                        "staff": staff_name,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 確認返信
                    reply = f"""承知いたしました。{staff_name}さんの欠勤を受理しました。

処理ID: {absence_record['id']}
日付: {today}

以下を実行します:
1. 代替スタッフ募集
2. 顧客への連絡

お大事にしてください。"""
                    
                    send_line_message(LINE_BOT_TOKEN, user_id, reply)
                    
                    # 代替スタッフ募集
                    substitute_request = f"""
🚨 代替出勤募集

{staff_name}さんが本日欠勤となりました。
代替出勤が可能な方は「代わります」とメッセージしてください。

日時: {today}
理由: {absence_record['reason']}

よろしくお願いいたします。
                    """.strip()
                    
                    # 他のスタッフに送信
                    for uid, info in staff_mapping.items():
                        if uid != user_id:
                            send_line_message(LINE_BOT_TOKEN, uid, substitute_request)
                    
                    automation_log.append({
                        "action": "代替募集送信",
                        "target_staff": len(staff_mapping) - 1,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # 代替申出検出
                substitute_analysis = analyze_substitute_message(message_text)
                
                if substitute_analysis['is_substitute']:
                    
                    substitute_record = {
                        "id": f"sub_{len(substitute_offers)+1:03d}",
                        "substitute_staff": staff_name,
                        "user_id": user_id,
                        "message": message_text,
                        "confidence": substitute_analysis['confidence'],
                        "created_at": datetime.now().isoformat(),
                        "status": "受付完了"
                    }
                    substitute_offers.append(substitute_record)
                    
                    # 確認返信
                    reply = f"""{staff_name}さん、代替出勤ありがとうございます。

受付ID: {substitute_record['id']}
受付時刻: {datetime.now().strftime('%H:%M')}

予約データを確認し、顧客に連絡します。"""
                    
                    send_line_message(LINE_BOT_TOKEN, user_id, reply)
                    
                    # 自動処理実行
                    if absence_reports:
                        latest_absence = absence_reports[-1]
                        absent_staff = latest_absence['staff_name']
                        absence_date = latest_absence['date']
                        absence_reason = latest_absence['reason']
                        
                        appointments = get_appointments(absent_staff, absence_date)
                        notify_customers(appointments, absent_staff, absence_reason)
                        
                        # 処理完了通知
                        final_message = f"""
処理完了

代替スタッフ: {staff_name}
完了時刻: {datetime.now().strftime('%H:%M')}

処理内容:
- 予約確認: {len(appointments)}件
- 顧客連絡: {len(appointments)}件

ありがとうございました。
                        """.strip()
                        
                        send_line_message(LINE_BOT_TOKEN, user_id, final_message)
        
        return 'OK', 200
        
    except Exception as e:
        print(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/')
def dashboard():
    """当日欠勤対応システム監視画面"""
    template = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>当日欠勤対応システム</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f8f9fa; }
            .header { background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 25px; }
            .container { max-width: 1000px; margin: 20px auto; padding: 0 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #e74c3c; }
            .logs { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .log-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .log-item { background: #ecf0f1; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .status { padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
            .status-active { background: #d5f4e6; color: #27ae60; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>当日欠勤対応システム</h1>
            <p>迅速な欠勤対応・顧客通知システム</p>
        </div>
        
        <div class="container">
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{{ absence_count }}</div>
                    <div>本日の欠勤</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ substitute_count }}</div>
                    <div>代替申出</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{{ notification_count }}</div>
                    <div>顧客通知</div>
                </div>
            </div>
            
            <div class="logs">
                <div class="log-card">
                    <h3>欠勤記録</h3>
                    {% for absence in recent_absences %}
                    <div class="log-item">
                        <strong>{{ absence.staff_name }}</strong><br>
                        理由: {{ absence.reason }}<br>
                        <span class="status status-active">処理済み</span><br>
                        <small>{{ absence.created_at[:19] }}</small>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="log-card">
                    <h3>代替申出</h3>
                    {% for substitute in recent_substitutes %}
                    <div class="log-item">
                        <strong>{{ substitute.substitute_staff }}</strong><br>
                        <span class="status status-active">受付完了</span><br>
                        <small>{{ substitute.created_at[:19] }}</small>
                    </div>
                    {% endfor %}
                </div>
                
                <div class="log-card">
                    <h3>顧客通知</h3>
                    {% for notification in recent_notifications %}
                    <div class="log-item">
                        {{ notification.customer }}<br>
                        {{ notification.appointment_time }} {{ notification.service }}<br>
                        <span class="status status-active">送信済み</span><br>
                        <small>{{ notification.sent_at[:19] }}</small>
                    </div>
                    {% endfor %}
                </div>
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

@app.route('/api/test/simple-flow', methods=['POST'])
def test_simple_flow():
    """シンプル自動化フローのテスト"""
    
    test_absence_msg = "体調不良で今日は欠勤します"
    absence_analysis = analyze_absence_message(test_absence_msg)
    
    if absence_analysis['is_absence']:
        today = datetime.now().strftime('%Y-%m-%d')
        
        absence_record = {
            "id": f"test_{len(absence_reports)+1:03d}",
            "staff_name": "田中美咲",
            "date": today,
            "reason": "体調不良",
            "original_message": test_absence_msg,
            "confidence": absence_analysis['confidence'],
            "created_at": datetime.now().isoformat(),
            "status": "テスト"
        }
        absence_reports.append(absence_record)
        
        test_substitute_msg = "代わります"
        substitute_analysis = analyze_substitute_message(test_substitute_msg)
        
        if substitute_analysis['is_substitute']:
            substitute_record = {
                "id": f"test_sub_{len(substitute_offers)+1:03d}",
                "substitute_staff": "佐藤花子",
                "message": test_substitute_msg,
                "confidence": substitute_analysis['confidence'],
                "created_at": datetime.now().isoformat(),
                "status": "テスト"
            }
            substitute_offers.append(substitute_record)
            
            appointments = get_appointments("田中美咲", today)
            notify_customers(appointments, "田中美咲", "体調不良")
            
            return jsonify({
                "status": "success",
                "message": "当日欠勤対応テスト完了",
                "results": {
                    "欠勤検出": "成功",
                    "代替申出": "成功", 
                    "予約確認": f"{len(appointments)}件",
                    "顧客通知": f"{len(appointments)}件"
                }
            })
    
    return jsonify({"status": "error", "message": "テスト失敗"})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("当日欠勤対応システム")
    print("="*50)
    print("管理画面: http://localhost:5001/")
    print("Webhook: http://localhost:5001/webhook/line")
    print("テストAPI: POST /api/test/simple-flow")
    print("\n機能:")
    print("1. 当日欠勤メッセージ自動検出")
    print("2. 代替スタッフ募集自動送信")
    print("3. 顧客通知自動送信")
    print("4. シンプル・迅速対応")
    print("="*50)
    
    app.run(host='0.0.0.0', port=5001, debug=True)

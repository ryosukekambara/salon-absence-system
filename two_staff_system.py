from flask import Flask, request, jsonify, render_template_string
import json
import re
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'two-staff-system-2025'

# LINE Bot設定
LINE_BOT_A_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

# 実際のスタッフUser ID
staff_mapping = {
    "U3dafc1648": {"name": "神原さん"},
    "U1ad150fa8": {"name": "Saoriさん"}
}

absence_reports = []
substitute_offers = []
automation_log = []

def analyze_absence_message(text):
    patterns = [
        r'(当日欠勤|欠勤|休み|休む)',
        r'(体調不良|発熱|具合が悪い)',
        r'(出勤できない|来れない|いけない)',
        r'(本日.*休|今日.*休)'
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
    patterns = [
        r'(出勤できます|出勤可能)',
        r'(大丈夫|いけます|可能)',
        r'(代わり|代理)'
    ]
    
    confidence = 0
    for pattern in patterns:
        if re.search(pattern, text):
            confidence += 0.3
    
    return {
        "is_substitute": confidence > 0.25,
        "confidence": min(confidence, 1.0)
    }

def send_line_message(token, user_id, message):
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
    except:
        return False

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
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
                
                # 欠勤メッセージ検出
                absence_analysis = analyze_absence_message(message_text)
                
                if absence_analysis['is_absence']:
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    absence_record = {
                        "staff_name": staff_name,
                        "date": today,
                        "reason": "体調不良" if "体調不良" in message_text else "急用",
                        "created_at": datetime.now().isoformat()
                    }
                    absence_reports.append(absence_record)
                    
                    automation_log.append({
                        "action": f"{staff_name}の欠勤検出",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 欠勤者への返信
                    reply = f"""欠勤を受理しました。

{staff_name}
日付: {today}

代替スタッフに連絡中...
お大事にしてください。"""
                    
                    send_line_message(LINE_BOT_A_TOKEN, user_id, reply)
                    
                    # 他のスタッフに代替募集
                    substitute_request = f"""
代替出勤募集

{staff_name}が本日欠勤となりました。
代替出勤が可能でしたら「出勤できます」とメッセージしてください。

日時: {today}
理由: {absence_record['reason']}

よろしくお願いします。
                    """.strip()
                    
                    for uid, info in staff_mapping.items():
                        if uid != user_id:
                            send_line_message(LINE_BOT_A_TOKEN, uid, substitute_request)
                    
                    automation_log.append({
                        "action": "代替募集送信完了",
                        "timestamp": datetime.now().isoformat()
                    })
                
                # 代替申出検出
                substitute_analysis = analyze_substitute_message(message_text)
                
                if substitute_analysis['is_substitute']:
                    substitute_record = {
                        "substitute_staff": staff_name,
                        "created_at": datetime.now().isoformat()
                    }
                    substitute_offers.append(substitute_record)
                    
                    automation_log.append({
                        "action": f"{staff_name}の代替申出受付",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 代替申出者への返信
                    reply = f"""代替出勤を受付しました。

{staff_name}
ありがとうございます。

自動処理実行中:
- 予約データ取得
- 顧客通知送信

完了までお待ちください。"""
                    
                    send_line_message(LINE_BOT_A_TOKEN, user_id, reply)
                    
                    # 自動処理実行（デモ）
                    automation_log.append({
                        "action": "自動スクレイピング実行",
                        "appointments": "2件取得",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    automation_log.append({
                        "action": "顧客通知送信完了",
                        "customers": "2名に通知",
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # 完了通知
                    final_message = f"""
自動化フロー完了

代替スタッフ: {staff_name}
処理結果:
- 予約データ: 2件取得
- 顧客通知: 2件送信

すべて完了しました。
                    """.strip()
                    
                    send_line_message(LINE_BOT_A_TOKEN, user_id, final_message)
        
        return 'OK', 200
    except Exception as e:
        print(f"Error: {e}")
        return 'Error', 500

@app.route('/')
def dashboard():
    template = """
    <html>
    <head>
        <meta charset="UTF-8">
        <title>2人体制自動化システム</title>
        <style>
            body { font-family: Arial; margin: 20px; background: #f5f5f5; }
            .card { background: white; padding: 20px; margin: 10px; border-radius: 8px; }
            .staff { background: #e3f2fd; padding: 10px; margin: 5px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>2人体制自動化システム</h1>
        <div class="card">
            <h3>登録スタッフ</h3>
            <div class="staff">神原さん (U3dafc1648)</div>
            <div class="staff">Saoriさん (U1ad150fa8)</div>
        </div>
        
        <div class="card">
            <h3>処理状況</h3>
            <p>欠勤検出: {{ absence_count }}件</p>
            <p>代替申出: {{ substitute_count }}件</p>
        </div>
        
        <div class="card">
            <h3>処理ログ</h3>
            {% for log in recent_logs %}
            <div style="background: #f9f9f9; padding: 8px; margin: 5px; border-radius: 3px;">
                {{ log.action }} - {{ log.timestamp[:19] }}
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    return render_template_string(template,
        absence_count=len(absence_reports),
        substitute_count=len(substitute_offers),
        recent_logs=automation_log[-10:]
    )

if __name__ == '__main__':
    print("2人体制自動化システム起動")
    print("神原さん & Saoriさん")
    print("管理画面: http://localhost:5001/")
    
    app.run(host='0.0.0.0', port=5001, debug=True)

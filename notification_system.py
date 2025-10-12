from flask import Flask, request, render_template_string
import requests
import os
import json
from datetime import datetime
from messages import MESSAGES
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
MAPPING_FILE = 'customer_mapping.json'

staff_mapping = {
    "U3dafc1648cc64b066ca1c5b3f4a67f8e": {"name": "神原さん", "salonboard_name": "與那城"},
    "U1ad150fa84a287c095eb98186a8cdc45": {"name": "Saoriさん", "salonboard_name": "沙織"}
}

def load_mapping():
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_mapping(customer_name, user_id):
    mapping = load_mapping()
    mapping[customer_name] = {
        "user_id": user_id,
        "registered_at": datetime.now().isoformat()
    }
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"顧客登録: {customer_name} → {user_id}")

def send_line_message(user_id, message):
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
    except:
        return False

@app.route('/')
def admin():
    template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>メッセージ管理</title>
    </head>
    <body>
        <h1>メッセージ管理画面</h1>
        <p><a href="/customers">→ 登録顧客一覧を見る</a></p>
        <form method="POST" action="/update">
            <div>
                <label>代替募集メッセージ:</label><br>
                <textarea name="absence_request" rows="5" cols="60">{{ messages.absence_request }}</textarea>
            </div>
            <div>
                <label>代替確定通知:</label><br>
                <textarea name="substitute_confirmed" rows="3" cols="60">{{ messages.substitute_confirmed }}</textarea>
            </div>
            <button type="submit">保存</button>
        </form>
    </body>
    </html>
    '''
    return render_template_string(template, messages=MESSAGES)

@app.route('/customers')
def customer_list():
    mapping = load_mapping()
    template = '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>顧客一覧</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>登録顧客一覧</h1>
        <p>合計: {{ mapping|length }}人</p>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #f0f0f0;">
                <th style="padding: 10px;">顧客名</th>
                <th style="padding: 10px;">LINE User ID</th>
                <th style="padding: 10px;">登録日時</th>
            </tr>
            {% for name, data in mapping.items() %}
            <tr>
                <td style="padding: 10px;">{{ name }}</td>
                <td style="padding: 10px;">{{ data.user_id if data.user_id else data }}</td>
                <td style="padding: 10px;">{{ data.registered_at if data.registered_at else '-' }}</td>
            </tr>
            {% endfor %}
        </table>
        <br>
        <a href="/">← メッセージ管理に戻る</a>
    </body>
    </html>
    '''
    return render_template_string(template, mapping=mapping)

@app.route('/update', methods=['POST'])
def update():
    absence_msg = request.form.get('absence_request')
    substitute_msg = request.form.get('substitute_confirmed')
    
    with open('messages.py', 'w', encoding='utf-8') as f:
        f.write(f'''MESSAGES = {{
    "absence_request": "{absence_msg}",
    "substitute_confirmed": "{substitute_msg}"
}}
''')
    
    return '<h2>保存完了</h2><p>システムを再起動してください</p><a href="/">戻る</a>'

@app.route('/webhook/line', methods=['POST'])
def webhook():
    try:
        events = request.json.get('events', [])
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                text = event['message']['text']
                staff_info = staff_mapping.get(user_id)
                
                # スタッフの場合
                if staff_info:
                    staff_name = staff_info['name']
                    
                    if "欠勤" in text or "休み" in text:
                        print(f"欠勤検出: {staff_name}")
                        for uid, info in staff_mapping.items():
                            if uid != user_id:
                                msg = MESSAGES["absence_request"].format(staff_name=staff_name)
                                send_line_message(uid, msg)
                    
                    elif "出勤" in text or "できます" in text:
                        print(f"代替申出検出: {staff_name}")
                        for uid, info in staff_mapping.items():
                            if uid != user_id:
                                notification = MESSAGES["substitute_confirmed"].format(substitute_name=staff_name)
                                send_line_message(uid, notification)
                
                # 一般顧客の場合（自動登録）
                else:
                    mapping = load_mapping()
                    # 既存顧客チェック
                    existing_customer = None
                    for name, data in mapping.items():
                        stored_id = data['user_id'] if isinstance(data, dict) else data
                        if stored_id == user_id:
                            existing_customer = name
                            break
                    
                    # 新規顧客で氏名らしいテキスト（2文字以上、スペース含む）
                    if not existing_customer and len(text) >= 2:
                        save_mapping(text, user_id)
                        print(f"新規顧客登録: {text}")
                        
        return 'OK', 200
    except Exception as e:
        print(f"Error: {e}")
        return 'Error', 500

if __name__ == '__main__':
    # 初回起動時にファイル作成
    if not os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE, 'w') as f:
            json.dump({}, f)
    
    print("管理画面: http://localhost:5001/")
    print("顧客一覧: http://localhost:5001/customers")
    app.run(host='0.0.0.0', port=5001, debug=True)

from flask import Flask, request, jsonify
import json
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

LINE_BOT_A_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

# 正しいUser IDに更新
staff_mapping = {
    "U3dafc1648cc64b066ca1c5b3f4a67f8e": {"name": "神原さん"},
    "U1ad150fa84a287c095eb98186a8cdc45": {"name": "Saoriさん"}
}

def send_line_message_debug(token, user_id, message):
    print(f"\n=== LINE送信デバッグ ===")
    print(f"送信先User ID: {user_id}")
    print(f"メッセージ: {message[:50]}...")
    
    if not token:
        print("❌ TOKENが設定されていません")
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
        print(f"API応答ステータス: {response.status_code}")
        print(f"API応答内容: {response.text}")
        
        if response.status_code == 200:
            print("✅ 送信成功")
            return True
        else:
            print("❌ 送信失敗")
            return False
            
    except Exception as e:
        print(f"❌ 送信エラー: {e}")
        return False

@app.route('/webhook/line', methods=['POST'])
def line_webhook():
    try:
        events = request.json.get('events', [])
        print(f"\n=== Webhook受信 ===")
        
        for event in events:
            if event['type'] == 'message' and event['message']['type'] == 'text':
                user_id = event['source']['userId']
                message_text = event['message']['text']
                
                print(f"送信者ID: {user_id}")
                print(f"メッセージ: {message_text}")
                
                staff_info = staff_mapping.get(user_id)
                if not staff_info:
                    print("❌ 未登録ユーザー")
                    continue
                
                staff_name = staff_info['name']
                print(f"✅ スタッフ認識: {staff_name}")
                
                # 欠勤メッセージテスト
                if "欠勤" in message_text or "休み" in message_text:
                    print(f"\n=== {staff_name}の欠勤検出 ===")
                    
                    # 他のスタッフに送信
                    for uid, info in staff_mapping.items():
                        if uid != user_id:
                            other_staff = info['name']
                            print(f"\n{other_staff}に代替募集送信開始...")
                            
                            substitute_request = f"""代替出勤募集

{staff_name}が本日欠勤となりました。
代替出勤が可能でしたら「出勤できます」とメッセージしてください。

よろしくお願いします。"""
                            
                            success = send_line_message_debug(LINE_BOT_A_TOKEN, uid, substitute_request)
                            
                            if success:
                                print(f"✅ {other_staff}への送信完了")
                            else:
                                print(f"❌ {other_staff}への送信失敗")
        
        return 'OK', 200
    except Exception as e:
        print(f"❌ Webhook処理エラー: {e}")
        return 'Error', 500

if __name__ == '__main__':
    print("修正版デバッグシステム起動")
    print("正しいUser ID設定済み")
    app.run(host='0.0.0.0', port=5001, debug=True)

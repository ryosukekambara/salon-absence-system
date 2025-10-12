from flask import Flask, request
import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

LINE_BOT_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

staff_mapping = {
    "U3dafc1648cc64b066ca1c5b3f4a67f8e": {"name": "神原さん"},
    "U1ad150fa84a287c095eb98186a8cdc45": {"name": "Saoriさん"}
}

@app.route('/webhook/line', methods=['POST'])
def webhook():
    try:
        print("=== メッセージ受信 ===")
        events = request.json.get('events', [])
        
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                text = event['message']['text']
                
                staff_info = staff_mapping.get(user_id)
                if staff_info:
                    staff_name = staff_info['name']
                    print(f"スタッフ: {staff_name}")
                    print(f"メッセージ: {text}")
                    
                    if "欠勤" in text or "休み" in text:
                        print("欠勤検出!")
                        
                    elif "出勤" in text or "できます" in text:
                        print("代替申出検出!")
                        
        return 'OK', 200
    except Exception as e:
        print(f"エラー: {e}")
        return 'Error', 500

if __name__ == '__main__':
    print("システム起動中...")
    app.run(host='0.0.0.0', port=5001, debug=True)

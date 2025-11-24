#!/usr/bin/env python3
import re

# auth_notification_system.pyを読み込み
with open('auth_notification_system.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 神原用Webhookを探して修正
webhook_code = '''
@app.route('/webhook/staff', methods=['POST'])
def line_webhook_staff():
    try:
        body = request.get_json()
        events = body.get('events', [])
        
        for event in events:
            if event['type'] == 'message':
                user_id = event['source']['userId']
                message_text = event.get('message', {}).get('text', '')
                
                # 神原さん（U3dafc1648cc64b066ca1c5b3f4a67f8e）からのメッセージ
                if user_id == 'U3dafc1648cc64b066ca1c5b3f4a67f8e':
                    print(f"[WEBHOOK] 神原さんからメッセージ: {message_text}", flush=True)
                    
                    # スクレイピング実行（バックグラウンド）
                    import subprocess
                    import threading
                    
                    def run_scrape():
                        try:
                            print(f"[SCRAPE] バックグラウンドで実行開始", flush=True)
                            result = subprocess.run(
                                ['python3', 'scrape_salonboard_bookings.py'],
                                capture_output=True,
                                text=True,
                                timeout=300
                            )
                            print(f"[SCRAPE] 完了: {result.returncode}", flush=True)
                            if result.stdout:
                                print(f"[SCRAPE] stdout: {result.stdout[:500]}", flush=True)
                            if result.stderr:
                                print(f"[SCRAPE] stderr: {result.stderr[:500]}", flush=True)
                        except Exception as e:
                            print(f"[SCRAPE] エラー: {str(e)}", flush=True)
                    
                    # 別スレッドで実行
                    threading.Thread(target=run_scrape, daemon=True).start()
                
                # プロフィール取得（自動登録）
                headers = {'Authorization': f'Bearer {LINE_BOT_TOKEN_STAFF}'}
                profile_url = f'https://api.line.me/v2/bot/profile/{user_id}'
                profile_response = requests.get(profile_url, headers=headers)
                
                if profile_response.status_code == 200:
                    profile = profile_response.json()
                    display_name = profile.get('displayName', 'Unknown')
                    
                    mapping = load_mapping()
                    if display_name not in mapping:
                        if save_mapping(display_name, user_id):
                            print(f"✅ 新規スタッフ登録: {display_name} ({user_id})")
                        else:
                            print(f"❌ スタッフ登録失敗: {display_name} ({user_id})")
                    else:
                        print(f"[情報] 既に登録済み（スタッフ）: {display_name} ({user_id})")
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f"❌ Webhook エラー（スタッフ）: {str(e)}")
        return jsonify({'status': 'error'}), 500
'''

# 既存のWebhookを置換
pattern = r'@app\.route\(\'/webhook/staff\', methods=\[\'POST\'\]\)\s+def line_webhook_staff\(\):.*?return jsonify\(\{\'status\': \'error\'\}\), 500'
content = re.sub(pattern, webhook_code.strip(), content, flags=re.DOTALL)

# 保存
with open('auth_notification_system.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Webhook更新完了")

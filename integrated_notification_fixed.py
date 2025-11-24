import json
import os
import glob
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class SalonNotificationSystem:
    def __init__(self):
        self.channel_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
        self.bookings = []
    
    def load_latest_scrape_result(self):
        json_files = glob.glob('scrape_result*.json')
        if not json_files:
            print("❌ スクレイピング結果ファイルが見つかりません")
            return False
        latest_file = max(json_files, key=os.path.getctime)
        print(f"📂 読み込み：{latest_file}")
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.bookings = data.get('bookings', [])
        print(f"📋 {len(self.bookings)}件の予約を処理します")
        return True
    
    def create_customer_message(self, booking):
        customer_name = booking.get('お客様名', '')
        if '\n' in customer_name:
            customer_name = customer_name.split('\n')[0]
        if '(' in customer_name:
            customer_name = customer_name.split('(')[0]
        customer_name = customer_name.replace('★', '').strip()
        datetime_str = booking.get('来店日時', '')
        staff = booking.get('スタッフ', '')
        staff_line = ""
        if '(指)' in staff:
            staff = staff.replace('(指)', '').strip()
            staff_line = f"担当：{staff}\n"
        menu = booking.get('メニュー', '').strip()
        menu_line = ""
        if menu and menu != '-':
            menu_line = f"{menu}\n"
        booking_details = f"{datetime_str}\n"
        if staff_line:
            booking_details += staff_line
        if menu_line:
            booking_details += menu_line
        msg = f"""{customer_name} 様
ご予約日の【3日前】となりましたので、お知らせいたします🕊️

【本店】
{booking_details}
『※ 注意点』は、すべてのお客様に快適にお過ごしいただくためのご案内です。
ご理解・ご協力のほど、よろしくお願いいたします🙇‍♀️

当日お会いできるのを楽しみにしております💐


※ 注意点
■ 遅刻について
スタッフ判断でメニュー変更や日時変更となる場合があり
当日中の時間変更であれば、【次回予約特典】はそのまま適用可能

＜次回予約特典が失効＞
予約日から3日前まで
前回来店日から3ヶ月経過

＜キャンセル料＞
◾️次回予約特典
当日変更：施術代金の50％

◾️通常予約
前日変更：施術代金の50％
当日変更：施術代金の100％"""
        return msg
    
    def send_line_message(self, user_id, message):
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {self.channel_token}'}
        data = {'to': user_id, 'messages': [{'type': 'text', 'text': message}]}
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"送信エラー：{e}")
            return False
    
    def send_test_notifications(self, test_user_id):
        if not self.bookings:
            print("予約データがありません")
            return
        test_bookings = [b for b in self.bookings if b.get('電話番号') == '09015992055']
        if not test_bookings:
            print("❌ テスト予約が見つかりません")
            return
        print(f"🧪 テストモード：{len(test_bookings)}件のテスト予約を神原にのみ送信")
        for booking in test_bookings:
            customer_msg = self.create_customer_message(booking)
            print("\n【顧客向けメッセージ】")
            print(customer_msg)
            result = self.send_line_message(test_user_id, customer_msg)
            if result:
                print("✅ テスト送信成功")
            else:
                print("❌ テスト送信失敗")

if __name__ == '__main__':
    print("=" * 60)
    print("サロンボード統合通知システム（テスト版）")
    print("=" * 60)
    system = SalonNotificationSystem()
    if not system.load_latest_scrape_result():
        exit(1)
    test_user_id = os.getenv('TEST_LINE_USER_ID')
    if not test_user_id:
        print("❌ TEST_LINE_USER_IDが設定されていません")
        exit(1)
    system.send_test_notifications(test_user_id)
    print("\n✅ 処理完了")
#!/usr/bin/env python3
"""3日前リマインド通知を送信"""
import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

headers_supabase = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

def send_line_message(user_id, message):
    """LINE通知を送信"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

def normalize_name(name):
    """名前を正規化（スペース・★除去）"""
    if not name:
        return ""
    return name.replace(" ", "").replace("　", "").replace("★", "").strip()

def main():
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST)
    target_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    
    print(f"[{today.strftime('%Y-%m-%d %H:%M')}] リマインド通知開始")
    print(f"対象日: {target_date}")
    
    # 3日後の予約を取得（bookingsテーブル）
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/bookings?date=eq.{target_date}&select=*',
        headers=headers_supabase
    )
    
    if response.status_code != 200:
        print(f"予約取得エラー: {response.status_code}")
        return
    
    bookings = response.json()
    print(f"予約件数: {len(bookings)} 件")
    
    if not bookings:
        print("対象予約なし")
        return
    
    # 顧客データを取得
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/customers?select=*',
        headers=headers_supabase
    )
    customers = response.json()
    
    # 電話番号→顧客マッピング
    phone_to_customer = {c['phone']: c for c in customers if c.get('phone')}
    # 名前→顧客マッピング（正規化）
    name_to_customer = {normalize_name(c['name']): c for c in customers if c.get('name')}
    
    sent_count = 0
    failed_count = 0
    no_match_count = 0
    
    for booking in bookings:
        customer_name = booking.get('customer_name', '')
        phone = booking.get('phone', '')
        time = booking.get('time', '')
        menu = booking.get('menu', '')
        
        # 顧客を検索（電話番号優先、次に名前）
        customer = None
        if phone and phone in phone_to_customer:
            customer = phone_to_customer[phone]
        else:
            normalized = normalize_name(customer_name)
            if normalized in name_to_customer:
                customer = name_to_customer[normalized]
        
        if not customer or not customer.get('line_user_id'):
            print(f"  ✗ マッチなし: {customer_name}")
            no_match_count += 1
            continue
        
        # リマインドメッセージ作成
        message = f"""【ご予約リマインド】
{customer_name}様

ご予約日時: {target_date} {time}
メニュー: {menu}

ご来店をお待ちしております。
eyelashsalon HAL"""
        
        # LINE送信
        if send_line_message(customer['line_user_id'], message):
            print(f"  ✓ 送信成功: {customer_name}")
            sent_count += 1
        else:
            print(f"  ✗ 送信失敗: {customer_name}")
            failed_count += 1
    
    print(f"\n結果: 送信成功={sent_count}, 失敗={failed_count}, マッチなし={no_match_count}")

if __name__ == "__main__":
    main()

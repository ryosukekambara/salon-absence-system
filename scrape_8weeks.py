#!/usr/bin/env python3
"""
8週間分の予約をサロンボードから取得してSupabaseに保存
"""
import json
import os
import requests
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_cookies():
    """session_cookies.jsonからクッキーを読み込む"""
    cookie_file = os.path.join(os.path.dirname(__file__), 'session_cookies.json')
    if os.path.exists(cookie_file):
        with open(cookie_file, 'r') as f:
            return json.load(f)
    return None

def scrape_date(page, target_date):
    """指定日の予約を取得"""
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://salonboard.com/KLP/reserve/reserveList/?search_date={date_str}"
    
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)
        
        # ログインページにリダイレクトされたかチェック
        if 'login' in page.url.lower():
            print(f"  ❌ ログインページにリダイレクト")
            return None
        
        bookings = []
        rows = page.query_selector_all('tr.reservation-row, tr[data-reservation-id]')
        
        if not rows:
            # 別のセレクタを試す
            rows = page.query_selector_all('table tbody tr')
        
        for row in rows:
            try:
                cells = row.query_selector_all('td')
                if len(cells) >= 4:
                    booking = {
                        'visit_datetime': target_date.strftime("%m/%d") + (cells[0].inner_text().strip() if cells else ''),
                        'customer_name': cells[1].inner_text().strip() if len(cells) > 1 else '',
                        'phone': cells[2].inner_text().strip() if len(cells) > 2 else '',
                        'menu': cells[3].inner_text().strip() if len(cells) > 3 else '',
                        'staff': cells[4].inner_text().strip() if len(cells) > 4 else '',
                    }
                    if booking['customer_name']:
                        bookings.append(booking)
            except Exception as e:
                continue
        
        return bookings
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return None

def save_to_supabase(bookings, target_date):
    """予約データをSupabaseに保存（upsert）"""
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    }
    
    saved = 0
    for booking in bookings:
        data = {
            'booking_id': f"{target_date.strftime('%Y%m%d')}_{booking.get('customer_name', '')}_{booking.get('visit_datetime', '')}",
            'customer_name': booking.get('customer_name', ''),
            'phone': booking.get('phone', ''),
            'visit_datetime': booking.get('visit_datetime', ''),
            'menu': booking.get('menu', ''),
            'staff': booking.get('staff', ''),
            'status': 'confirmed',
            'booking_source': 'salonboard'
        }
        
        res = requests.post(
            f'{SUPABASE_URL}/rest/v1/bookings',
            headers=headers,
            json=data
        )
        
        if res.status_code in [200, 201]:
            saved += 1
    
    return saved

def main():
    print(f"[{datetime.now()}] 8週間分の予約取得開始")
    
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST)
    
    cookies = get_cookies()
    if not cookies:
        print("❌ session_cookies.jsonが見つかりません")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        
        total_bookings = 0
        
        # 8週間分（56日）をループ
        for day_offset in range(56):
            target_date = today + timedelta(days=day_offset)
            print(f"[{target_date.strftime('%Y-%m-%d')}] スクレイピング中...")
            
            bookings = scrape_date(page, target_date)
            
            if bookings:
                saved = save_to_supabase(bookings, target_date)
                print(f"  ✅ {len(bookings)}件取得, {saved}件保存")
                total_bookings += saved
            elif bookings == []:
                print(f"  予約なし")
            else:
                print(f"  ❌ 取得失敗")
            
            # レート制限対策
            page.wait_for_timeout(2000)
        
        browser.close()
    
    print(f"\n完了: 合計 {total_bookings}件 保存")

if __name__ == "__main__":
    main()

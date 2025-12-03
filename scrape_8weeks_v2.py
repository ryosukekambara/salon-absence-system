#!/usr/bin/env python3
"""
8週間分の予約をスクレイピングしてbookingsテーブルに保存
scrape_today.pyのログイン方式を流用
"""
import json
import re
import os
import requests
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

def login_to_salonboard(page):
    login_id = os.environ.get('SALONBOARD_LOGIN_ID', 'CD18317')
    login_password = os.environ.get('SALONBOARD_LOGIN_PASSWORD', 'Ne8T2Hhi!')
    
    page.goto('https://salonboard.com/login/', timeout=60000)
    page.wait_for_timeout(3000)
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', login_password)
    page.click('a:has-text("ログイン")')
    page.wait_for_timeout(5000)
    
    return 'login' not in page.url.lower()

def scrape_date(page, target_date, headers, supabase_url):
    """指定日の予約を取得してbookingsに保存"""
    date_str = target_date.strftime('%Y%m%d')
    url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={date_str}'
    
    page.goto(url, timeout=90000)
    page.wait_for_timeout(2000)
    
    bookings_saved = 0
    rows = page.query_selector_all('table tbody tr')
    
    for row in rows:
        try:
            cells = row.query_selector_all('td')
            if len(cells) < 4:
                continue
            
            time_text = cells[0].text_content().strip() if cells[0] else ''
            customer_name = cells[2].text_content().strip() if len(cells) > 2 else ''
            phone = cells[3].text_content().strip() if len(cells) > 3 else ''
            menu = cells[5].text_content().strip() if len(cells) > 5 else ''
            staff = cells[1].text_content().strip() if len(cells) > 1 else ''
            
            # 名前から★などを除去
            customer_name = re.sub(r'[★☆♪♡⭐️🦁]', '', customer_name).strip()
            customer_name = re.sub(r'\([A-Z]{2}\d+\)', '', customer_name).strip()
            
            if not customer_name:
                continue
            
            # 電話番号を数字のみに
            phone_clean = re.sub(r'[^\d]', '', phone)
            
            # booking_id生成
            booking_id = f"{date_str}_{time_text}_{phone_clean}".replace(" ", "").replace(":", "").replace("~", "")
            
            data = {
                'booking_id': booking_id,
                'customer_name': customer_name,
                'phone': phone_clean,
                'visit_datetime': f"{target_date.strftime('%m/%d')}{time_text}",
                'menu': menu,
                'staff': staff,
                'status': 'confirmed',
                'booking_source': 'salonboard'
            }
            
            # Upsert
            res = requests.post(
                f'{supabase_url}/rest/v1/bookings',
                headers={**headers, 'Prefer': 'resolution=merge-duplicates'},
                json=data
            )
            
            if res.status_code in [200, 201]:
                bookings_saved += 1
                
        except Exception as e:
            continue
    
    return bookings_saved

def main():
    print(f"[{datetime.now(JST)}] 8週間予約スクレイピング開始")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    today = datetime.now(JST)
    total_saved = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='ja-JP',
            timezone_id='Asia/Tokyo'
        )
        
        # クッキー読み込み
        try:
            with open('session_cookies.json', 'r') as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
        except:
            pass
        
        page = context.new_page()
        
        # 最初のページでログイン確認
        test_url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={today.strftime("%Y%m%d")}'
        page.goto(test_url, timeout=90000)
        page.wait_for_timeout(3000)
        
        if 'login' in page.url.lower() or len(page.query_selector_all('table')) == 0:
            print("ログインが必要です...")
            if not login_to_salonboard(page):
                print("ログイン失敗")
                browser.close()
                return {"success": False, "error": "ログイン失敗"}
            
            # クッキー保存
            new_cookies = context.cookies()
            with open('session_cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2, ensure_ascii=False)
            print("ログイン成功、クッキー保存")
        
        # 8週間分（56日）をスクレイピング
        for day_offset in range(56):
            target_date = today + timedelta(days=day_offset)
            saved = scrape_date(page, target_date, headers, SUPABASE_URL)
            total_saved += saved
            print(f"  {target_date.strftime('%Y-%m-%d')}: {saved}件保存")
        
        browser.close()
    
    print(f"\n完了: 合計 {total_saved}件 保存")
    return {"success": True, "total": total_saved}

if __name__ == "__main__":
    main()

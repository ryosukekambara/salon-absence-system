#!/usr/bin/env python3
"""
8週間分の予約をスクレイピングしてbookingsテーブルに保存
scrape_today.pyをそのまま流用、期間を8週間に拡張
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
        
        try:
            with open('session_cookies.json', 'r') as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
        except:
            pass
        
        page = context.new_page()
        
        # ログイン確認
        test_url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={today.strftime("%Y%m%d")}'
        page.goto(test_url, timeout=90000)
        page.wait_for_timeout(3000)
        
        if 'login' in page.url.lower() or 'エラー' in page.title() or len(page.query_selector_all('table')) == 0:
            print("ログインが必要です...")
            if not login_to_salonboard(page):
                print("ログイン失敗")
                browser.close()
                return {"success": False, "error": "ログイン失敗"}
            
            new_cookies = context.cookies()
            with open('session_cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2, ensure_ascii=False)
            print("ログイン成功、クッキー保存")
        
        # 8週間分（56日）をスクレイピング
        for day_offset in range(56):
            target_date = today + timedelta(days=day_offset)
            date_str = target_date.strftime('%Y%m%d')
            url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={date_str}'
            
            page.goto(url, timeout=90000)
            page.wait_for_timeout(2000)
            
            bookings = []
            seen_ids = set()
            rows = page.query_selector_all('table tbody tr')
            
            for row in rows:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 4:
                        continue
                    
                    customer_name = cells[2].text_content().strip()
                    id_match = re.search(r'\(([A-Z]{2}\d+)\)', customer_name)
                    booking_id = id_match.group(1) if id_match else None
                    
                    if not booking_id or booking_id in seen_ids:
                        continue
                    seen_ids.add(booking_id)
                    
                    source = cells[4].text_content().strip() if len(cells) > 4 else ""
                    bookings.append({'booking_id': booking_id, 'source': source})
                except:
                    continue
            
            print(f"  [{target_date.strftime('%Y-%m-%d')}] {len(bookings)}件検出")
            
            # 詳細ページから情報取得してbookingsに保存
            for booking in bookings:
                try:
                    bid = booking['booking_id']
                    source = booking['source']
                    
                    if source == "NHPB":
                        detail_url = f'https://salonboard.com/KLP/reserve/net/reserveDetail/?reserveid={bid}'
                    else:
                        detail_url = f'https://salonboard.com/KLP/reserve/ext/extReserveDetail/?reserveid={bid}'
                    
                    page.goto(detail_url, timeout=60000)
                    page.wait_for_timeout(1500)
                    
                    # 電話番号
                    phone_cell = page.query_selector('tr:has-text("電話番号") td:nth-child(2)')
                    phone = phone_cell.text_content().strip() if phone_cell else ""
                    phone_match = re.search(r'(0\d{9,10})', phone)
                    phone = phone_match.group(1) if phone_match else ""
                    
                    # 顧客名
                    name_cell = page.query_selector('tr:has-text("お客様名") td:nth-child(2)')
                    full_name = name_cell.text_content().strip() if name_cell else ""
                    full_name = re.sub(r'[★☆♪♡⭐️🦁]', '', full_name).strip()
                    
                    # 来店日時
                    datetime_cell = page.query_selector('tr:has-text("来店日時") td:nth-child(2)')
                    visit_datetime = datetime_cell.text_content().strip() if datetime_cell else ""
                    
                    # メニュー
                    menu_cell = page.query_selector('tr:has-text("メニュー") td:nth-child(2)')
                    menu = menu_cell.text_content().strip() if menu_cell else ""
                    
                    # スタッフ
                    staff_cell = page.query_selector('tr:has-text("担当") td:nth-child(2)')
                    staff = staff_cell.text_content().strip() if staff_cell else ""
                    
                    if full_name:
                        data = {
                            'booking_id': bid,
                            'customer_name': full_name,
                            'phone': phone,
                            'visit_datetime': visit_datetime,
                            'menu': menu,
                            'staff': staff,
                            'status': 'confirmed',
                            'booking_source': source
                        }
                        
                        res = requests.post(
                            f'{SUPABASE_URL}/rest/v1/bookings',
                            headers={**headers, 'Prefer': 'resolution=merge-duplicates'},
                            json=data
                        )
                        
                        if res.status_code in [200, 201]:
                            total_saved += 1
                            print(f"    保存: {full_name} | {phone}")
                except Exception as e:
                    print(f"    エラー: {e}")
                    continue
        
        browser.close()
    
    print(f"\n完了: 合計 {total_saved}件 保存")
    return {"success": True, "total": total_saved}

if __name__ == "__main__":
    main()

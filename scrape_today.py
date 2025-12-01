#!/usr/bin/env python3
"""
当日の予約をスクレイピングして、電話番号をcustomersテーブルに追加
毎日21時に実行
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

def normalize_name(name):
    if not name:
        return ""
    return re.sub(r'[\s　★☆♪♡⭐️🦁()（）]', '', name)

def main():
    print(f"[{datetime.now(JST)}] 当日予約スクレイピング開始")
    
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    today = datetime.now(JST).strftime('%Y%m%d')
    
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
        url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={today}'
        
        page.goto(url, timeout=90000)
        page.wait_for_timeout(3000)
        
        if 'login' in page.url.lower() or 'エラー' in page.title() or len(page.query_selector_all('table')) == 0:
            if not login_to_salonboard(page):
                browser.close()
                return
            
            new_cookies = context.cookies()
            with open('session_cookies.json', 'w') as f:
                json.dump(new_cookies, f, indent=2, ensure_ascii=False)
            
            page.goto(url, timeout=90000)
            page.wait_for_timeout(3000)
        
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
        
        print(f"[SCRAPE] {len(bookings)}件の予約を検出")
        
        updated = 0
        for booking in bookings:
            try:
                bid = booking['booking_id']
                source = booking['source']
                
                if source == "NHPB":
                    detail_url = f'https://salonboard.com/KLP/reserve/net/reserveDetail/?reserveid={bid}'
                else:
                    detail_url = f'https://salonboard.com/KLP/reserve/ext/extReserveDetail/?reserveid={bid}'
                
                page.goto(detail_url)
                page.wait_for_timeout(2000)
                
                phone_cell = page.query_selector('tr:has-text("電話番号") td:nth-child(2)')
                phone = phone_cell.text_content().strip() if phone_cell else ""
                phone_match = re.search(r'(0\d{9,10})', phone)
                phone = phone_match.group(1) if phone_match else ""
                
                name_cell = page.query_selector('tr:has-text("お客様名") td:nth-child(2)')
                full_name = name_cell.text_content().strip() if name_cell else ""
                
                if phone and full_name:
                    res = requests.get(
                        f'{SUPABASE_URL}/rest/v1/customers?select=id,name,phone&phone=is.null',
                        headers=headers
                    )
                    customers = res.json()
                    
                    for cust in customers:
                        cust_name = normalize_name(cust.get('name', ''))
                        sb_name = normalize_name(full_name)
                        
                        if cust_name and sb_name and (cust_name in sb_name or sb_name in cust_name):
                            update_res = requests.patch(
                                f"{SUPABASE_URL}/rest/v1/customers?id=eq.{cust['id']}",
                                headers=headers,
                                json={'phone': phone}
                            )
                            if update_res.status_code in [200, 204]:
                                print(f"✅ {cust.get('name')} → {phone}")
                                updated += 1
                            break
            except Exception as e:
                continue
        
        browser.close()
    
    print(f"[完了] {updated}件の電話番号を追加")

if __name__ == "__main__":
    main()
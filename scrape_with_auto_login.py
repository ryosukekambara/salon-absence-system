#!/usr/bin/env python3
"""
自動ログイン方式のスクレイピング
クッキー依存をなくし、毎回ID/パスワードでログイン
"""
import json
import re
import os
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

def login_to_salonboard(page):
    """サロンボードに自動ログイン"""
    login_id = os.environ.get('SALONBOARD_LOGIN_ID', 'CD18317')
    login_password = os.environ.get('SALONBOARD_LOGIN_PASSWORD', 'Ne8T2Hhi!')
    
    print("[LOGIN] ログインページにアクセス...")
    page.goto('https://salonboard.com/login/', timeout=60000)
    page.wait_for_timeout(3000)
    
    print("[LOGIN] ID入力...")
    page.fill('input[name="userId"]', login_id)
    page.wait_for_timeout(500)
    
    print("[LOGIN] パスワード入力...")
    page.fill('input[name="password"]', login_password)
    page.wait_for_timeout(500)
    
    print("[LOGIN] ログインボタンクリック...")
    page.click('a:has-text("ログイン")')
    page.wait_for_timeout(10000)
    
    if 'login' in page.url.lower():
        print("[LOGIN] ログイン失敗")
        return False
    
    print(f"[LOGIN] ログイン成功: {page.url}")
    return True

def scrape_bookings(days_ahead):
    """予約をスクレイピング"""
    target_date = (datetime.now(JST) + timedelta(days=days_ahead)).strftime('%Y%m%d')
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        if not login_to_salonboard(page):
            browser.close()
            return {"bookings": [], "error": "ログイン失敗"}
        
        url = f'https://salonboard.com/KLP/reserve/reserveList/searchDate?date={target_date}'
        print(f"[SCRAPE] 予約ページにアクセス ({target_date})...")
        page.goto(url, timeout=60000)
        page.wait_for_timeout(3000)
        
        bookings = []
        rows = page.query_selector_all('table tbody tr')
        print(f"[SCRAPE] {len(rows)}行を検出")
        
        seen_ids = set()
        for row in rows:
            cells = row.query_selector_all('td')
            if len(cells) < 5:
                continue
            
            link = row.query_selector('a[href*="reserveId="]')
            if not link:
                continue
            href = link.get_attribute('href')
            match = re.search(r'reserveId=([A-Z0-9]+)', href)
            if not match:
                continue
            reserve_id = match.group(1)
            if reserve_id in seen_ids:
                continue
            seen_ids.add(reserve_id)
            
            datetime_text = cells[0].text_content().strip()
            customer_name = cells[1].text_content().strip()
            staff = cells[2].text_content().strip() if len(cells) > 2 else ""
            menu = cells[3].text_content().strip() if len(cells) > 3 else ""
            status = cells[4].text_content().strip() if len(cells) > 4 else ""
            
            if not datetime_text or not customer_name:
                continue
            
            bookings.append({
                "予約ID": reserve_id,
                "来店日時": datetime_text,
                "お客様名": customer_name,
                "スタッフ": staff,
                "メニュー": menu,
                "ステータス": status
            })
        
        print(f"[SCRAPE] {len(bookings)}件の予約を取得")
        browser.close()
        
        return {
            "bookings": bookings,
            "date": target_date,
            "scraped_at": datetime.now(JST).isoformat()
        }

if __name__ == "__main__":
    result = scrape_bookings(7)
    print(json.dumps(result, ensure_ascii=False, indent=2))

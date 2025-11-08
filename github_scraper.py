#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import os
import json
from datetime import datetime

def scrape_reservations():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # ログイン
        print("ログイン中...")
        page.goto('https://salonboard.com/login/')
        page.fill('input[name="userId"]', os.getenv('SALONBOARD_LOGIN_ID'))
        page.fill('input[name="password"]', os.getenv('SALONBOARD_LOGIN_PASSWORD'))
        page.press('input[name="password"]', 'Enter')
        
        page.wait_for_timeout(5000)
        
        if 'KLP' in page.url or 'top' in page.url:
            print("✅ ログイン成功")
            
            # 予約ページへ
            page.goto('https://salonboard.com/KLP/reserve/reserveList/')
            page.wait_for_timeout(3000)
            
            # データ取得（簡易版）
            content = page.content()
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'url': page.url,
                'content_length': len(content)
            }
            
            with open('scrape_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"✅ スクレイピング成功: {len(content)} bytes")
        else:
            print("❌ ログイン失敗")
            result = {'status': 'login_failed'}
            with open('scrape_result.json', 'w') as f:
                json.dump(result, f, indent=2)
        
        browser.close()

if __name__ == '__main__':
    scrape_reservations()

#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import json

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    page.press('input[name="password"]', 'Enter')
    
    # ログイン完了を待つ
    page.wait_for_url('**/KLP/**', timeout=30000)
    print("✅ ログイン成功！")
    
    # Cookieを取得
    cookies = context.cookies()
    
    # 重要なCookieだけを保存
    important_cookies = [c for c in cookies if 'JSESSIONID' in c['name'] or 'HPB_LOGIN_KEY' in c['name']]
    
    # JSON形式で保存
    with open('session_cookies.json', 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"\n📁 Cookieを保存しました")
    print(f"Cookie数: {len(cookies)}")
    
    page.wait_for_timeout(3000)
    browser.close()

import os
from playwright.sync_api import sync_playwright
import json

SALONBOARD_ID = os.getenv('SALONBOARD_LOGIN_ID')
SALONBOARD_PW = os.getenv('SALONBOARD_LOGIN_PASSWORD')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    
    # クッキー読み込み
    try:
        with open('session_cookies.json', 'r') as f:
            cookies = json.load(f)
            context.add_cookies(cookies)
    except:
        pass
    
    page = context.new_page()
    page.goto('https://salonboard.com/KLP/schedule/salonSchedule/?date=20251216', timeout=60000)
    page.wait_for_timeout(3000)
    
    if 'login' in page.url.lower():
        print("ログインが必要")
    else:
        # スタッフ行のHTML構造を確認
        html = page.content()
        with open('schedule_sample.html', 'w') as f:
            f.write(html)
        print("schedule_sample.html に保存しました")
    
    browser.close()

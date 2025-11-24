#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("ブラウザが開きます...")
    page.goto("https://salonboard.com/login/")
    
    print("\n" + "="*60)
    print("手動でログインしてください")
    print("ログイン完了後、このターミナルに戻って Enter を押してください")
    print("="*60)
    
    input("\n完了したら Enter を押してください...")
    
    # クッキーを保存
    cookies = page.context.cookies()
    with open('session_cookies.json', 'w') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"\n✅ クッキーを保存しました: {len(cookies)}個")
    print("✅ ファイル: session_cookies.json")
    
    browser.close()

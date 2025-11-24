#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    print("1. ログインページへアクセス")
    page.goto('https://salonboard.com/login/')
    
    print("2. ID/パスワード入力")
    page.wait_for_selector('input[name="userId"]')
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    
    print("3. JavaScriptで直接ログイン関数を実行")
    # dologin() 関数を直接呼び出す
    page.evaluate('dologin()')
    
    print("4. 5秒待機")
    page.wait_for_timeout(5000)
    
    print(f"5. 現在のURL: {page.url}")
    
    # エラーメッセージを確認
    body_text = page.text_content('body')
    if 'エラー' in body_text or '失敗' in body_text:
        print("\n⚠️ エラーが見つかりました:")
        for line in body_text.split('\n'):
            line = line.strip()
            if 'エラー' in line or '失敗' in line or '間違' in line:
                print(f"  {line}")
    else:
        print("\n✅ エラーなし")
    
    if 'KLP' in page.url:
        print("\n🎉 ログイン成功！")
    else:
        print("\n❌ ログイン失敗")
    
    input("\nEnterキーを押すと終了...")
    browser.close()

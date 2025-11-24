#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
load_dotenv()

print("ブラウザを起動します...")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # ブラウザを表示
        slow_mo=1000     # 1秒ずつゆっくり動作
    )
    page = browser.new_page()
    page.set_default_timeout(60000)  # 1分
    
    try:
        print("サロンボードにアクセス中...")
        page.goto('https://salonboard.com/login/', wait_until='domcontentloaded')
        print("✅ アクセス成功！")
        input("Enterキーを押すと終了します...")
    except Exception as e:
        print(f"❌ エラー: {e}")
    finally:
        browser.close()

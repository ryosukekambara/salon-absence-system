#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # ← headless無効
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    
    print("Headless=False テスト開始...")
    start = time.time()
    try:
        page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=60000)
        print(f"成功: {round(time.time()-start, 2)}秒")
        print(f"URL: {page.url}")
        input("Enterキーを押して終了...")
    except Exception as e:
        print(f"失敗: {round(time.time()-start, 2)}秒")
        print(f"エラー: {e}")
    browser.close()

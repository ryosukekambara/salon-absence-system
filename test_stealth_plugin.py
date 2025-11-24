#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 正しいステルスモード適用
    stealth = Stealth()
    stealth.apply_stealth_sync(page)
    
    print("playwright-stealth でテスト開始...")
    start = time.time()
    try:
        page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=60000)
        print(f"成功: {round(time.time()-start, 2)}秒")
        print(f"URL: {page.url}")
        print(f"タイトル: {page.title()}")
    except Exception as e:
        print(f"失敗: {round(time.time()-start, 2)}秒")
        print(f"エラー: {e}")
    browser.close()

#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    page = browser.new_page()
    
    # 全イベントをログ
    page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
    page.on("pageerror", lambda err: print(f"[PAGE_ERROR] {err}"))
    page.on("request", lambda req: print(f"[REQUEST] {req.method} {req.url}"))
    page.on("response", lambda res: print(f"[RESPONSE] {res.status} {res.url}"))
    
    print("page.goto開始...")
    start = time.time()
    try:
        page.goto('https://salonboard.com/login/', wait_until='domcontentloaded', timeout=60000)
        print(f"成功: {round(time.time()-start, 2)}秒")
    except Exception as e:
        print(f"失敗: {round(time.time()-start, 2)}秒")
        print(f"エラー: {e}")
    
    input("Enterで終了...")
    browser.close()

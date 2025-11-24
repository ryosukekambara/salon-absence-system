#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    def handle_request_failed(request):
        if 'doLogin' in request.url or 'KLP' in request.url:
            print(f"❌ リクエスト失敗: {request.url}")
            print(f"   Failure: {request.failure}")
    
    page.on("requestfailed", handle_request_failed)
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    
    print("\nEnterキーを押す...")
    page.press('input[name="password"]', 'Enter')
    
    page.wait_for_timeout(10000)
    
    print(f"\n最終URL: {page.url}")
    
    if 'KLP' in page.url:
        print("✅ ログイン成功！")
    else:
        print("❌ ログイン失敗")
    
    browser.close()

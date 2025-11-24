#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    def handle_request(request):
        if 'doLogin' in request.url:
            print(f"\n📤 リクエスト送信")
    
    def handle_request_finished(request):
        if 'doLogin' in request.url:
            print(f"\n✅ リクエスト完了")
            try:
                response = request.response()
                print(f"Status: {response.status}")
                body = response.text()
                print(f"Body: {body}")
            except Exception as e:
                print(f"エラー: {e}")
    
    def handle_request_failed(request):
        if 'doLogin' in request.url:
            print(f"\n❌ リクエスト失敗")
            print(f"Failure: {request.failure}")
    
    page.on("request", handle_request)
    page.on("requestfinished", handle_request_finished)
    page.on("requestfailed", handle_request_failed)
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    page.wait_for_timeout(3000)
    
    print("\nクリック...")
    page.click('a.common-CNCcommon__primaryBtn.loginBtnSize', no_wait_after=True)
    
    print("20秒待機...")
    page.wait_for_timeout(20000)
    
    print(f"\n最終URL: {page.url}")
    browser.close()

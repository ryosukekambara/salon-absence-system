#!/usr/bin/env python3
import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import json

load_dotenv()

captured_requests = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # すべてのリクエストをキャプチャ
    def handle_request(request):
        if 'login' in request.url.lower():
            captured_requests.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data
            })
    
    page.on('request', handle_request)
    
    login_id = os.getenv('SALONBOARD_LOGIN_ID')
    password = os.getenv('SALONBOARD_LOGIN_PASSWORD')
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    
    # Enterでログイン
    page.press('input[name="password"]', 'Enter')
    
    page.wait_for_timeout(10000)
    
    print(f"最終URL: {page.url}")
    
    browser.close()

# 保存
with open('captured_headers.json', 'w') as f:
    json.dump(captured_requests, f, indent=2)

print("\n=== キャプチャしたリクエスト ===")
for i, req in enumerate(captured_requests):
    print(f"\n{i+1}. {req['method']} {req['url']}")
    if req['post_data']:
        print(f"   POST Data: {req['post_data'][:100]}")

print(f"\n詳細は captured_headers.json に保存しました")

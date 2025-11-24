#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

captured_posts = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    def log_request(request):
        if request.method == 'POST' and 'salonboard.com' in request.url:
            captured_posts.append({
                'url': request.url,
                'data': request.post_data
            })
            print(f"POST: {request.url}")
    
    page.on('request', log_request)
    
    page.goto('https://salonboard.com/login/')
    page.fill('input[name="userId"]', os.getenv('SALONBOARD_LOGIN_ID'))
    page.fill('input[name="password"]', os.getenv('SALONBOARD_LOGIN_PASSWORD'))
    page.press('input[name="password"]', 'Enter')
    
    page.wait_for_timeout(5000)
    
    print(f"\n最終URL: {page.url}")
    
    for post in captured_posts:
        print(f"\nPOST URL: {post['url']}")
        print(f"Data: {post['data']}")
    
    browser.close()

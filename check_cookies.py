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
    
    page.goto('https://salonboard.com/login/')
    page.wait_for_selector('input[name="userId"]')
    page.wait_for_timeout(3000)
    
    # Cookie確認
    cookies = page.context.cookies()
    print("\n=== Cookies ===")
    print(f"Cookie数: {len(cookies)}")
    
    # ページ内のトークンを確認
    print("\n=== CSRF/Hidden Fields ===")
    hidden_inputs = page.query_selector_all('input[type="hidden"]')
    print(f"Hidden fields数: {len(hidden_inputs)}")
    
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    
    print("\n=== 送信前のフォームデータ ===")
    form_data = page.evaluate('''() => {
        const form = document.querySelector('form');
        if (!form) return 'フォームなし';
        const data = new FormData(form);
        const obj = {};
        for (let [key, value] of data.entries()) {
            obj[key] = value;
        }
        return obj;
    }''')
    print(form_data)
    
    browser.close()

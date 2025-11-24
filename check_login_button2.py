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
    page.fill('input[name="userId"]', login_id)
    page.fill('input[name="password"]', password)
    
    print("=== onclick*='login' の詳細 ===")
    elements = page.query_selector_all('[onclick*="login"]')
    for i, elem in enumerate(elements):
        html = elem.evaluate('el => el.outerHTML')
        text = elem.text_content()
        print(f"\n[{i}] テキスト: '{text}'")
        print(f"    HTML: {html[:300]}")
    
    page.screenshot(path='login_page.png')
    browser.close()
